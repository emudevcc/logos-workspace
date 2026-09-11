---
phase: 2
title: "Retry and Resilience Hardening"
status: pending
priority: P1
effort: "2.5h"
dependencies: [1]
---

# Phase 2: Retry and Resilience Hardening

## Goal

Close the failure class that still gets zero retries and no useful
correction today — a syntactically valid JSON response that fails
`BibleStudy.model_validate` (right JSON, wrong shape) — with a retry hint
that can actually fix it. Fix a real, shipped bug in the 429 path (it sleeps
twice per retried attempt). Document the resulting worst-case latency
correctly instead of inventing a new enforcement mechanism.

<!-- Updated: Red Team Review Session 2026-09-11 — the original design
wrapped the retry loop in `asyncio.timeout`/`wait_for` with a new
`llm_study_deadline_seconds` setting. All three reviewers independently
flagged this as unsafe (cancelling a request on the process-wide shared
`httpx.AsyncClient` used by every cockpit has no verified safety guarantee)
and the chosen default (45s) was below the existing per-call timeout (60s),
making the mechanism self-defeating. That mechanism is REMOVED. This phase
instead fixes the two things that actually made worst-case latency worse
than it needed to be: the missing schema-mismatch retry, and the 429
double-sleep bug — neither requires new settings, new constructor wiring, or
any cancellation risk. -->

## Context Links

- `app/services/bible_studies.py:223-247` — `_build_report`'s retry loop
  only retries when `attempt == 0 and isinstance(exc, LLMJsonValidationError)`
  (after Phase 1); a `pydantic.ValidationError` from
  `BibleStudy.model_validate(raw)` at line 245 is raised immediately with no
  retry.
- `app/schemas/bible.py:87` — `lexical_exegesis: list[LexicalItem] =
  Field(default_factory=list, max_length=3)`. The prompt at
  `bible_studies.py:133-134` asks for "2-3 pivotal original-language words" —
  the schema and prompt agree on the count; a `ValidationError` here means
  the model didn't follow that instruction (returned 4+ items, or a field of
  the wrong type), not that the repo's own prompt/schema pair are in
  conflict. The fix is a better retry hint, not a prompt/schema edit.
- `app/services/llm.py:113-131` — `_post_completions`'s retry loop: on
  `attempt > 0` it unconditionally sleeps a jittered backoff
  (`min(4.0, 0.5 * 2**(attempt-1)) * random.uniform(0.5, 1.0)`) at the *top*
  of the loop, then, if the *previous* response was a 429 with a usable
  `Retry-After`, it *also* sleeps that duration inside the 429 branch before
  `continue`-ing. Both sleeps fire for the same retried attempt.
- `app/core/config.py:64-66` — `llm_timeout_seconds` (60.0 default),
  `llm_max_retries` (3 default, meaning **4** total network attempts per
  `complete_json` call — the original draft's "3 attempts" was off by one).

## Key Insights

- The JSON-shape retry and the schema-validation retry are the same kind of
  problem — the model produced something unusable — but they need *different*
  corrective hints. The existing `_JSON_RETRY_HINT` says "return only valid
  JSON, no markdown fences" — correct for a syntax problem, useless for a
  shape problem where the JSON already parsed fine. A schema mismatch needs
  the model told *which* fields were wrong, via Pydantic's own
  `exc.errors()` (field paths + short messages only — never
  `exc.errors(include_input=True)`'s input values, which could echo
  sensitive model output back into the next prompt for no benefit).
- The two-level retry (network in `llm.py`, business logic in
  `bible_studies.py`) is an intentional design already in place; this phase
  does not flatten it or bound it with a new deadline. It fixes one concrete
  bug (double-sleep) that was making the existing network-level retry loop
  slower than its own backoff formula intends, and documents the resulting
  worst case in settings terms operators already have.
- Budget accounting (`SpendBudget.consume()` in `llm.py:85-86`) is called
  once per `complete_json` call, so the business-level retry correctly
  spends a second unit of daily budget for a second real upstream call —
  this is accurate cost accounting and this phase leaves it unchanged. The
  schema-mismatch retry is capped at one attempt, same as the existing
  JSON-validation retry, so this doesn't change the worst-case cost per
  study beyond what Phase 1's widened `LLMJsonValidationError` already
  implied.
- Fixing the double-sleep bug is also the deadline problem's real answer:
  removing one full sleep per retried network attempt shrinks the existing
  worst case without adding a single line of new configuration or any risk
  to the shared `httpx.AsyncClient`.

## Requirements

- [x] Add `LLMSchemaMismatchError(LLMError)` in `app/services/bible_studies.py`
      (not `llm.py` — it wraps a Pydantic `ValidationError`, which only
      exists after a successful `complete_json` call).
- [x] Restructure `_build_report` so `BibleStudy.model_validate(raw)` and its
      `ValidationError` handling sit *inside* the same `for attempt in
      range(2):` loop as the `complete_json` call (see "Architecture" for
      the exact control flow — this avoids the `UnboundLocalError` risk of a
      naive restructure), so a schema mismatch on attempt 0 falls through to
      attempt 1 with a corrective hint, exactly like `LLMJsonValidationError`
      does today.
- [x] Add a new `_schema_retry_hint(exc: ValidationError, language: str) ->
      str` function that renders `exc.errors()`'s `(loc, msg)` pairs (field
      path + Pydantic's short message, nothing from `input`) into a short,
      localized (es/en/pt) instruction appended to the system prompt on the
      retry attempt — distinct from `_JSON_RETRY_HINT`, which stays reserved
      for genuine JSON-syntax failures.
- [x] In `routes_bible.py::create_study`, add an `isinstance(exc,
      LLMSchemaMismatchError)` branch before the generic `LLMError` fallback,
      returning the same friendly-Spanish-detail pattern already used for
      `LLMJsonValidationError` (Spanish default, matching the route's
      existing friendly-message convention — this plan does not add
      per-language friendly messages beyond what already exists).
- [x] Fix the 429 double-sleep in `_post_completions`: when a `Retry-After`
      sleep was honored for a 429 on the current attempt, skip the
      unconditional jittered backoff at the top of the *next* iteration for
      that one transition. The jittered backoff still applies normally to
      5xx retries and to 429s with no usable `Retry-After` header.
- [x] Add a short paragraph to `docs/DEPLOYMENT.md`, next to the existing
      `LLM_MAX_RETRIES`/`LLM_TIMEOUT_SECONDS` documentation, stating the
      corrected worst-case latency formula for one `POST /api/bible/study`
      call: up to 2 business attempts × up to `(LLM_MAX_RETRIES + 1)`
      network attempts × up to `LLM_TIMEOUT_SECONDS` each, plus up to one
      15-second `Retry-After` wait per network attempt that hits a 429 (not
      compounded with the backoff, after this phase's fix). Do not add a new
      setting to enforce this number — this is documentation of the existing
      configuration's implication, not a new control.

## Architecture

```
_build_report()
  report: BibleStudy | None = None
  last_error: LLMError | None = None
  for attempt in range(2):
    hint = "" if last_error is None else _hint_for(last_error, language)
    try:
      raw = await self._llm.complete_json(system=system + hint, user=user, ...)
    except LLMJsonValidationError as exc:
      last_error = exc
      if attempt == 0: continue
      raise
    try:
      report = BibleStudy.model_validate(raw)
      break
    except ValidationError as exc:
      last_error = LLMSchemaMismatchError(f"Estudo bíblico: resposta fora do esquema: {_format(exc.errors())}")
      if attempt == 0: continue
      raise last_error
  if report is None:  # pragma: no cover - defensive; loop above always breaks or raises
    raise last_error or LLMError("Estudo bíblico: falha sem erro registrado")

_hint_for(last_error, language):
  if isinstance(last_error, LLMJsonValidationError): return _JSON_RETRY_HINT[language]
  if isinstance(last_error, LLMSchemaMismatchError): return _schema_retry_hint(last_error.errors, language)

llm.py._post_completions() — 429 double-sleep fix
  honored_retry_after = False
  for attempt in range(self._max_retries + 1):
    if attempt > 0 and not honored_retry_after:
      await asyncio.sleep(jittered_backoff)
    honored_retry_after = False
    ... post ...
    if status == 429:
      retry_after = _retry_after_seconds(response)
      if retry_after is not None and retry_after <= 15:
        await asyncio.sleep(retry_after)
        honored_retry_after = True
      continue
```

## Related Code Files

- Modify: `app/services/bible_studies.py`
- Modify: `app/services/llm.py`
- Modify: `app/api/routes_bible.py`
- Modify: `docs/DEPLOYMENT.md`

## Implementation Steps

1. In `app/services/llm.py`, add a `honored_retry_after` boolean local to
   `_post_completions`, initialized `False` before the loop and reset to
   `False` at the top of each iteration (before the backoff check). Gate the
   top-of-loop jittered `asyncio.sleep` on `attempt > 0 and not
   honored_retry_after`. Set it to `True` immediately after the 429 branch's
   `Retry-After` sleep. Leave every other branch (5xx, transport errors,
   429s without a usable header) sleeping the backoff exactly as today.
2. Add `LLMSchemaMismatchError(LLMError)` in `bible_studies.py`, storing the
   parsed `exc.errors()` list (or a formatted string of it) so the retry
   hint function can use it without re-parsing.
3. Add `_format(errors: list) -> str` and `_schema_retry_hint(errors, lang)
   -> str` helpers rendering each error's `loc`/`msg` (not `input`) into one
   short sentence per language, appended as the retry-attempt hint.
4. Restructure `_build_report` per the Architecture block: move
   `BibleStudy.model_validate` and its `except ValidationError` inside the
   `for attempt in range(2):` loop, replace the old post-loop `if raw is
   None: raise last_error` guard with the `if report is None:` guard shown
   above, and route hint selection through `_hint_for`.
5. In `routes_bible.py::create_study`, add the `LLMSchemaMismatchError`
   branch to the exception ladder (after the Phase 1 `LLMBudgetExceeded`/
   `LLMNotConfiguredError`/`LLMJsonValidationError` branches, before the
   generic fallback).
6. Add the worst-case-latency paragraph to `docs/DEPLOYMENT.md`.
7. Run `ruff check app/services/bible_studies.py app/services/llm.py app/api/routes_bible.py` + `mypy app` + `pytest tests/backend/test_bible.py tests/backend/test_llm.py -q`.

## Todo List

- [x] 429 double-sleep fixed (`honored_retry_after` gate)
- [x] `LLMSchemaMismatchError` added, carrying structured field errors
- [x] Field-path-aware retry hint (`_schema_retry_hint`), distinct from the JSON-syntax hint
- [x] `_build_report` restructured with the `report`/`last_error` guard shown above (no `UnboundLocalError` path)
- [x] Friendly Spanish detail message for schema mismatch in the route
- [x] `docs/DEPLOYMENT.md` documents the corrected worst-case latency (no new setting)
- [x] `ruff` + `mypy` + backend tests green

## Success Criteria

- A `BibleStudy.model_validate` failure on the first attempt is followed by
  a second `complete_json` call whose system prompt contains the specific
  field path(s) that failed validation (verified by the Phase 4 test
  asserting on prompt content, not just call count).
- A 429 with a usable `Retry-After` header produces exactly one
  `asyncio.sleep` call for that attempt, not two (verified by the corrected
  Phase 4 test).
- The Spanish detail message for a schema mismatch reads as a translated
  sentence, never a raw Pydantic `ValidationError` repr with `input_value`
  data in it.
- `docs/DEPLOYMENT.md` states a specific worst-case-latency number derived
  from the actual configured defaults, not the plan's original (incorrect)
  arithmetic.

## Risk Assessment

- **Risk:** Retrying on `LLMSchemaMismatchError` doubles the "wrong shape"
  failure's cost (two LLM calls instead of one) for what might be a
  persistently malformed prompt/schema pairing rather than a one-off model
  slip. **Mitigation:** capped at one retry, matching the existing
  `json_validate_failed` policy — no unbounded retries. If Phase 3's logging
  later shows sustained `LLMSchemaMismatchError`s for the same field, that's
  a prompt-tuning follow-up, not a retry-policy problem.
- **Risk:** The `_hint_for` dispatch silently does nothing if `last_error` is
  some other `LLMError` subtype that reaches attempt 1 (shouldn't happen
  given the two `except` clauses above, but worth a defensive check).
  **Mitigation:** the restructured loop only ever sets `last_error` to
  `LLMJsonValidationError` or `LLMSchemaMismatchError`; add an `assert` or a
  third `else: return ""` branch in `_hint_for` rather than letting it raise
  `AttributeError` on an unexpected type.
- **Risk (rejected mechanism, recorded for future reference):** an enforced
  wall-clock deadline via `asyncio.timeout`/`wait_for` around the retry loop
  was considered and rejected — see the note at the top of this file. If a
  future need for a hard latency SLA arises, prefer a per-`httpx`-call
  `timeout=` override (already plumbed via `self._timeout` in `llm.py`)
  over task-cancellation on the shared client, and budget a dedicated spike
  to verify cancellation safety before relying on it.

## Security Considerations

- `_schema_retry_hint` must render only `loc` and `msg` from
  `exc.errors()`, never `input` — Pydantic v2's default `errors()` call
  already omits input values unless `include_input=True` is passed
  explicitly; do not pass that argument.
- The friendly detail message for `LLMSchemaMismatchError` must not echo the
  raw Pydantic `ValidationError` (which can include field values from the
  model's output) back to the client; use a fixed, generic sentence like the
  existing `json_validate_failed` message does, and rely on Phase 1's
  `app/main.py` truncation fix as a second layer for any `LLMError`-family
  message that reaches the global handler through a path other than this
  route's own friendly branch.

## Next Steps

- Phase 3 logs both the retry and the final outcome of this hardened path,
  including which typed exception triggered it.
- Phase 4 adds the regression tests for the schema-mismatch retry (with a
  content assertion, not a tautological mock) and the corrected
  single-sleep 429 behavior.
