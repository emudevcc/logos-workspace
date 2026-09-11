---
phase: 1
title: "Typed LLM Error Taxonomy"
status: pending
priority: P1
effort: "2.5h"
dependencies: []
---

# Phase 1: Typed LLM Error Taxonomy

## Goal

Replace every place that classifies an LLM failure by parsing message text —
in Python *and* in JavaScript — with classification by exception type
(backend) or by the `ApiError.status` field that already exists but is
unused (frontend). Fix the two routing bugs the red-team review found this
duplication was hiding: `LLMBudgetExceeded` silently becoming a 502, and an
untruncated error message reaching the client.

<!-- Updated: Red Team Review Session 2026-09-11 — added the frontend
`error.status` fix (Finding 4), the `LLMBudgetExceeded` passthrough fix
(Finding 6), the truncation-at-source fix (Finding 7), the substring-fallback
visibility requirement (Finding 13), and widened the typed exception to cover
`complete_json`'s own JSON-decode failures, not just Groq's 400. -->

## Context Links

- `app/services/llm.py:100-106` — `complete_json` raises a bare `LLMError` on
  `json.JSONDecodeError` or a non-dict JSON body; `app/services/llm.py:112-140`
  — `_post_completions`; on a non-200 the error message is free text.
- `app/services/llm.py:143-150` — `_extract_content` raises a bare `LLMError`
  embedding the *entire* response dict or content string, untruncated.
- `app/services/bible_studies.py:112-114` — `_is_json_failure()` re-derives
  classification from that free-text message.
- `app/api/routes_bible.py:86-94` — `create_study()` repeats the identical
  substring check, and its `except LLMError as exc:` catches
  `LLMBudgetExceeded` (a subclass) too, routing it to the generic 502 branch
  instead of letting it bubble to the app's own 429 handler.
- `app/main.py:280-286` — `_register_exception_handlers` already maps
  `LLMBudgetExceeded` → 429 and the base `LLMError` → 502, but
  `routes_bible.py:86` intercepts both before they can reach either handler,
  and the base handler at `app/main.py:286` returns `str(exc)` with **no**
  truncation.
- `static/js/lib/api.js:3-7` — `ApiError` already carries `this.status`
  (the real HTTP status code) alongside `message` (the `detail` string).
- `static/js/components/bible_study.js:251-258` — `run()`'s catch block
  ignores `error.status` and instead does
  `const limited = /\b429\b/.test(error.message);` to decide whether to show
  the rate-limited message and reveal the Retry button.

## Key Insights

- The classification logic is duplicated in **three** places today, not two:
  `bible_studies.py` (Python, backend retry decision), `routes_bible.py`
  (Python, HTTP status decision), and `bible_study.js` (JavaScript, UI retry
  affordance). All three parse the same free-text message independently.
- The frontend duplication is the more dangerous one: `ApiError` already
  exposes the real status code (`static/js/lib/api.js:3-7`), so the regex on
  `error.message` is not filling a gap — it is a workaround that happens to
  work today only because the current 502 message for a 429-turned-into-a-
  retry-exhaustion case still contains the literal text `429`. Any wording
  change anywhere in the retry/error path (including ones later phases of
  this very plan would have made) can silently break it.
- `app/services/llm.py` is shared by every cockpit (English grammar/PREP/
  writing coaches, Português grammar coach, Bíblia studies). Typed exceptions
  and the truncation fix here benefit all of them; nothing in this phase is
  Bíblia-specific except the `routes_bible.py` and `bible_study.js` edits.
- `LLM_BASE_URL` is configurable (`app/core/config.py:59-62`), so a future
  non-Groq provider may not emit an `error.code` field at all — structural
  detection must fall back to the existing substring heuristic rather than
  assume every provider matches Groq's shape. Because that fallback trusts
  upstream-controlled text to decide whether a failure is retryable (and
  therefore billable a second time), it must be visible in logs (Phase 3),
  not just present in code.
- `_JSON_SHAPE`/`complete_json`'s own malformed-JSON path
  (`llm.py:100-106`) and Groq's structured `json_validate_failed` 400 are the
  *same* failure class from the caller's point of view — the model produced
  something unusable — so both should raise the same typed exception rather
  than only the 400 case getting a name.

## Requirements

- [x] Add `LLMJsonValidationError(LLMError)` to `app/services/llm.py`.
- [x] Keep the existing `LLMError`, `LLMNotConfiguredError`, `LLMBudgetExceeded`
      hierarchy; `LLMJsonValidationError` is a new subclass of `LLMError`, not
      a replacement.
- [x] Raise `LLMJsonValidationError` (not bare `LLMError`) from **all** of:
      the 400-with-`json_validate_failed` path in `_post_completions`; the
      substring-fallback path (`"Failed to generate JSON" in response.text`)
      in the same method, for providers without a structured `error.code`;
      the `json.JSONDecodeError` path in `complete_json` (`llm.py:100-103`);
      and the non-dict-JSON path in `complete_json` (`llm.py:104-105`).
- [x] Add a module-level `_truncate(text: str, limit: int = 200) -> str`
      helper in `llm.py` and use it in every `LLMError`/`LLMJsonValidationError`
      message that embeds upstream or model text, including
      `_extract_content` (`llm.py:143-150`), which today embeds the full,
      untruncated response dict/content string.
- [x] Fix `app/main.py:284-286`'s global `LLMError` handler to truncate
      `str(exc)` to 200 characters before returning it, as defense-in-depth
      for any `LLMError`-family message assembled outside `llm.py` (e.g. a
      Pydantic `ValidationError` repr from `bible_studies.py`, which Phase 2
      will still embed some of even after this fix).
- [x] Update `bible_studies.py`'s retry check in `_build_report` (currently
      `_is_json_failure(exc)`) to `isinstance(exc, LLMJsonValidationError)`;
      delete `_is_json_failure()`.
- [x] Update `routes_bible.py::create_study`'s `except LLMError as exc:`
      block: add `if isinstance(exc, LLMBudgetExceeded): raise` as the
      **first** branch (before the `LLMNotConfiguredError` check, order
      doesn't matter between these two but it must precede the generic
      fallback) so the budget-exceeded case reaches `app/main.py:280-282`'s
      429 handler instead of the generic 502; replace the substring check
      with `isinstance(exc, LLMJsonValidationError)` for the friendly-message
      branch.
- [x] In `static/js/components/bible_study.js`'s `run()` catch block, replace
      `const limited = /\b429\b/.test(error.message);` with
      `const limited = error.status === 429;`.
- [x] Log at `WARNING` (see Phase 3) whenever the substring-fallback
      detection path fires instead of the structural `error.code` check, so a
      provider whose error shape drifts from Groq's is visible rather than
      silently retried and billed twice on every occurrence.
- [x] Do not change any other friendly-message text or retry behavior beyond
      what's listed above — this phase is about *how* failures are detected
      and routed, not about adding new retryable failure classes (that is
      Phase 2's job, for schema mismatches specifically).

## Architecture

```
llm.py.complete_json() / _post_completions() response handling
  status 429/5xx                                    -> retry (unchanged)
  status 400 + error.code == "json_validate_failed"  -> raise LLMJsonValidationError (structural)
  status 400 + "Failed to generate JSON" in text     -> raise LLMJsonValidationError (fallback; log WARNING)
  other non-200                                      -> raise LLMError (unchanged)
  200 + json.JSONDecodeError                         -> raise LLMJsonValidationError (was bare LLMError)
  200 + non-dict JSON                                -> raise LLMJsonValidationError (was bare LLMError)
  all LLMError-family messages                       -> truncated via _truncate()

bible_studies.py::_build_report
  except LLMJsonValidationError as exc:
    if attempt == 0: retry
    else: raise
  except LLMError as exc:
    raise  # unchanged — non-JSON-shape failures still never retry here

routes_bible.py::create_study
  except LLMError as exc:
    if isinstance(exc, LLMBudgetExceeded): raise           # -> app-level 429 handler
    if isinstance(exc, LLMNotConfiguredError): raise        # -> app-level 503 handler (unchanged)
    if isinstance(exc, LLMJsonValidationError): friendly 502 detail
    else: raise HTTPException(502, str(exc)[:200])          # unchanged fallback

app/main.py exception_handler(LLMError)
  return JSONResponse(502, {"detail": str(exc)[:200]})      # was untruncated

bible_study.js run() catch
  const limited = error.status === 429;                    # was /\b429\b/.test(error.message)
```

## Related Code Files

- Modify: `app/services/llm.py`
- Modify: `app/services/bible_studies.py`
- Modify: `app/api/routes_bible.py`
- Modify: `app/main.py`
- Modify: `static/js/components/bible_study.js`

## Implementation Steps

1. In `app/services/llm.py`, add `class LLMJsonValidationError(LLMError):`
   next to the existing exception classes, and a private `_truncate(text,
   limit=200)` helper (`return text if len(text) <= limit else text[:limit]`).
2. In `complete_json`, wrap the existing `json.loads(content)` failure and
   the non-dict-body check to raise `LLMJsonValidationError` (using
   `_truncate` on the embedded content) instead of bare `LLMError`.
3. In `_post_completions`, when `response.status_code == 400`, attempt
   `response.json()` inside a `try/except (json.JSONDecodeError, ValueError)`;
   if it parses and `data.get("error", {}).get("code") == "json_validate_failed"`,
   raise `LLMJsonValidationError`. If parsing fails or the code doesn't
   match, check `"Failed to generate JSON" in response.text` before raising
   the same typed exception (log a `WARNING` here — see Phase 3 — noting the
   fallback path fired); otherwise fall through to the existing generic
   `LLMError` raise for other 400s. Use `_truncate` on all embedded text.
4. Apply `_truncate` inside `_extract_content` (`llm.py:143-150`) for both
   raise sites.
5. In `app/services/bible_studies.py`, import `LLMJsonValidationError` from
   `app.services.llm`, change the `except LLMError as exc:` branch in
   `_build_report` to check `isinstance(exc, LLMJsonValidationError)`, and
   delete `_is_json_failure()`.
6. In `app/api/routes_bible.py`, import `LLMJsonValidationError` and
   `LLMBudgetExceeded`, and reorder/rewrite `create_study`'s exception
   handling per the Architecture block above — the `LLMBudgetExceeded` branch
   must `raise` (not return an HTTPException) so FastAPI's registered
   exception handler at `app/main.py:280-282` runs.
7. In `app/main.py`, change `_llm_error`'s body to
   `JSONResponse(status_code=502, content={"detail": str(exc)[:200]})`.
8. In `static/js/components/bible_study.js`, change the `limited` check as
   specified. Confirm no other file reads `error.message` for the same
   purpose: `grep -rn "429" static/js/`.
9. Run `ruff check app/services/llm.py app/services/bible_studies.py app/api/routes_bible.py app/main.py` and `mypy app`.
10. Run `pytest tests/backend/test_llm.py tests/backend/test_bible.py -q` —
    note that `tests/backend/test_bible.py:437`'s existing test **will fail**
    at this point because its `FlakyLLM` test double raises a bare
    `LLMError`, not `LLMJsonValidationError`; fixing that test is Phase 4's
    job (do not fix it ad hoc here — Phase 4 documents exactly why and how).
    It is expected and correct for this phase to leave that one test red;
    confirm no *other* test in either file newly fails.

## Todo List

- [x] `LLMJsonValidationError` exception class + `_truncate()` helper added
- [x] `complete_json`'s own JSON-decode/non-dict-body failures raise the typed exception
- [x] Structural detection + logged substring fallback in `_post_completions`
- [x] `_extract_content` messages truncated
- [x] `_is_json_failure()` deleted; `bible_studies.py` uses `isinstance`
- [x] `LLMBudgetExceeded` re-raised (not swallowed) in `routes_bible.py`
- [x] Global `LLMError` handler truncates its response in `app/main.py`
- [x] `bible_study.js` classifies rate-limiting via `error.status`, not a message regex
- [x] `ruff` + `mypy` clean
- [x] `test_bible.py:437` confirmed red for the documented reason; no other test newly fails

## Success Criteria

- No file under `app/` contains the literal string `"json_validate_failed"`
  outside of `app/services/llm.py`; `grep -rn "json_validate_failed" app/`
  returns exactly one match.
- `grep -n "429" static/js/components/bible_study.js` returns zero matches
  in the `run()` function's catch block (the regex is gone).
- A manual request that triggers `LLMBudgetExceeded` (e.g. temporarily set
  `LLM_DAILY_LIMIT=1` and issue two studies) returns HTTP 429 from
  `/api/bible/study`, not 502.
- `app/main.py`'s `LLMError` handler never returns more than 200 characters
  in its `detail` field, verified by a manual request against a
  deliberately-broken `LLM_BASE_URL`.

## Risk Assessment

- **Risk:** A provider other than Groq returns a 400 with a differently-shaped
  error body, so the structural check never matches and only the substring
  fallback fires. **Mitigation:** the substring fallback stays in
  `_post_completions` (moved, not removed), and now logs a `WARNING` when it
  fires (Phase 3), making an unexpected upstream shape visible instead of
  silently doubling spend on every occurrence (Finding 13).
- **Risk:** `response.json()` on a 400 body raises if the body isn't valid
  JSON at all (e.g. an HTML error page from a misconfigured `LLM_BASE_URL`).
  **Mitigation:** wrap the parse in `try/except`; any parse failure falls
  through to the substring/generic path, never raises unhandled.
- **Risk:** Deferring the `test_bible.py:437` fix to Phase 4 leaves one red
  test between phases if they're implemented and merged separately.
  **Mitigation:** this is intentional and documented (step 10) — if Phases
  1 and 4 are implemented as one continuous session (the normal case), the
  red window never reaches a commit boundary; if they are split across
  separate work sessions, say so explicitly before committing Phase 1 alone.

## Security Considerations

- No new data is logged or persisted beyond what Phase 3 specifies; this
  phase's own change is the truncation fix (reducing exposure, not adding
  any).
- The `LLMBudgetExceeded` passthrough fix does not expose new information —
  it corrects the HTTP status code the client already receives a `detail`
  string for.

## Next Steps

- Phase 2 builds the schema-mismatch retry on top of this typed exception
  (and adds a second one, `LLMSchemaMismatchError`, for the Pydantic
  `ValidationError` case) and fixes the 429 double-sleep bug.
- Phase 4 fixes `test_bible.py`'s `FlakyLLM` double and adds the dedicated
  `LLMJsonValidationError` unit tests this phase's step 10 intentionally
  leaves red.
