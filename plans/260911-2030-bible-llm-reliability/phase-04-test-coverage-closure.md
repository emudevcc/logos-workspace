---
phase: 4
title: "Test Coverage Closure"
status: pending
priority: P1
effort: "2.5h"
dependencies: [1, 2, 3]
---

# Phase 4: Test Coverage Closure

## Goal

Add the regression tests for every behavior this plan introduces or fixes,
with assertions that can actually fail: the corrected single-sleep 429
behavior (Phase 2's bug fix), the new typed exceptions (Phase 1), the
schema-mismatch retry with a content-bearing hint (Phase 2), the
`LLMBudgetExceeded` → 429 routing fix (Phase 1), and the repaired
`FlakyLLM` test double the plan's own Phase 1 intentionally leaves red.

<!-- Updated: Red Team Review Session 2026-09-11 — the original phase
specified a `Retry-After` test asserting a single captured sleep duration
against code that (before Phase 2's fix) produces two; and a
schema-mismatch retry test that mocked success unconditionally regardless
of what the retry hint actually said, so it could never fail. Both are
corrected below to match Phase 2's redesigned behavior. Also added: a new
`chat_response`-style helper for error bodies (the existing one only builds
success payloads), a dedicated `LLMBudgetExceeded`-routing test, and a note
on why no new frontend component-test harness is added for the `error.status`
fix. -->

## Context Links

- `tests/backend/test_llm.py` — existing coverage: `test_complete_json_returns_parsed_object`,
  `test_retries_on_transient_5xx_then_succeeds`, `test_4xx_raises_llm_error_without_retry`,
  `test_disabled_when_no_api_key`, `test_invalid_json_content_raises`,
  `test_non_object_json_raises`. No test exercises `_retry_after_seconds` or
  the 429 sleep path it feeds.
- `tests/backend/test_bible.py:424-453` — the one existing `json_validate_failed`
  retry test (added in commit `7f4ae49`); its `FlakyLLM` double
  (`test_bible.py:428-440`) raises a **bare `LLMError`**, which after Phase 1
  no longer matches `isinstance(exc, LLMJsonValidationError)` — this test is
  red after Phase 1 until this phase fixes the double.
- `tests/backend/helpers.py:94` — `chat_response()` builds a Groq
  **success** payload (`{"choices": [{"message": {"content": ...}}]}`); it
  cannot express `{"error": {"code": "json_validate_failed"}}`, so the new
  structural-detection test needs a second helper.
- `tests/frontend/api.test.js:28-40` — already proves `ApiError.status`
  carries the real HTTP status code; Phase 1's `bible_study.js` fix relies
  on that existing guarantee, it doesn't need a new test to establish it.

## Key Insights

- `test_4xx_raises_llm_error_without_retry` asserts a plain 400 is *not*
  retried at the `llm.py` level — that test must keep passing unmodified
  after Phase 1, since `LLMJsonValidationError` is still an `LLMError` and
  `_post_completions` still only retries on 429/5xx, never on 400. Phase 1
  changes *which exception type* a 400 with `json_validate_failed` raises,
  not whether `llm.py` retries it. Use a body that does **not** match either
  the structural or fallback JSON-failure detection (e.g. a generic `{"error":
  {"code": "invalid_request_error"}}`) so this test keeps proving the
  *non*-JSON-failure 400 path.
- The `Retry-After` sleep is the behavior most at risk of a silent
  regression, since nothing today would fail if it stopped working —
  `asyncio.sleep` calls with the wrong duration don't raise, they just wait
  the wrong amount of time. Testing it means monkeypatching
  `asyncio.sleep` (via `monkeypatch.setattr("app.services.llm.asyncio.sleep",
  ...)`) to capture *every* call's duration in order, not just the first.
- After Phase 2's double-sleep fix, a 429 with a usable `Retry-After` header
  should produce **exactly one** captured sleep for that attempt — this is
  now a precise, non-tautological assertion (`sleeps == [3.0]`), not the
  "3.0 in sleeps" fudge the original draft would have needed.
- A schema-mismatch retry test only proves something if the mocked second
  call's system prompt is inspected for the *specific* field-path content
  Phase 2's `_schema_retry_hint` is supposed to inject — mocking the second
  call to unconditionally return a valid payload (regardless of what prompt
  it received) proves only that two calls happened, not that the hint
  mechanism works.
- `run()` in `static/js/components/bible_study.js` is a private closure
  inside `init(slot)`, not exported, and no test file in `tests/frontend/`
  mounts a full component (they test `static/js/lib/*` units only). Adding
  a component-mount test harness just for the one-line `error.status` fix
  would be new test infrastructure disproportionate to the change; this
  phase verifies that fix by grep + the existing `api.test.js` guarantee
  (`ApiError.status` is real) plus a manual check, and says so explicitly
  rather than silently skipping frontend coverage.

## Requirements

- [x] `tests/backend/helpers.py`: add `chat_error_response(status, code, message="boom")`
      building `{"error": {"code": code, "message": message}}` (or reuse an
      equivalent existing helper if one already exists), used by the new
      `test_llm.py` typed-exception tests.
- [x] `tests/backend/test_llm.py`: add a test that a 429 response carrying a
      numeric `Retry-After: 3` header causes the client to sleep for exactly
      `3.0` seconds for that attempt and no additional backoff sleep
      (monkeypatched `asyncio.sleep` capturing an ordered list; assert
      `sleeps == [3.0]` after Phase 2's fix, not `3.0 in sleeps`).
- [x] `tests/backend/test_llm.py`: add a test that a 429 with **no**
      `Retry-After` header falls back to the jittered backoff sleep (assert
      exactly one sleep call, with a duration `&lt;= 4.0`).
- [x] `tests/backend/test_llm.py`: add a test that a Groq 400 with
      `{"error": {"code": "json_validate_failed"}}` (via the new
      `chat_error_response` helper) raises `LLMJsonValidationError`
      specifically (not just `LLMError`); re-verify
      `test_4xx_raises_llm_error_without_retry` still passes unmodified with
      a body that matches neither detection path.
- [x] `tests/backend/test_llm.py`: add a test that malformed JSON content in
      a 200 response (existing `test_invalid_json_content_raises` body) and
      non-dict JSON content (existing `test_non_object_json_raises` body)
      now raise `LLMJsonValidationError` specifically — extend those two
      existing tests' assertions rather than duplicating them.
- [x] `tests/backend/test_bible.py`: fix `FlakyLLM` (around line 428) to
      raise `LLMJsonValidationError` (imported from `app.services.llm`)
      instead of a bare `LLMError`, restoring the existing retry test to
      green under Phase 1's `isinstance` check.
- [x] `tests/backend/test_bible.py`: add a test that a first-attempt
      `BibleStudy.model_validate` failure (mock `complete_json` to return
      JSON with, e.g., 4 `lexical_exegesis` items on attempt 1, a valid
      payload on attempt 2) succeeds via Phase 2's retry, **and** assert the
      second call's system prompt contains the specific field path from the
      first failure's `ValidationError` (e.g. the string `lexical_exegesis`),
      not just that a second call happened.
- [x] `tests/backend/test_bible.py`: add a test that a *second* consecutive
      schema mismatch (both attempts return invalid shapes) surfaces the
      friendly Spanish detail message via the route, not a raw
      `ValidationError` repr with `input_value` data in it.
- [x] `tests/backend/test_bible.py` or `tests/backend/test_routes_*.py`
      (whichever file already covers `routes_bible.py`'s exception-to-HTTP
      mapping — check for an existing pattern before choosing): add a test
      that `LLMBudgetExceeded` raised by the service surfaces as HTTP 429
      from `/api/bible/study`, not 502.
- [x] Confirm the full backend suite count grows from the 244-test baseline
      (commit `7f4ae49`'s message) by at least 8, and `ruff check` / `mypy
      app` stay clean.
- [x] Run `npm test` (frontend) once to confirm the `bible_study.js` edit
      didn't break existing frontend tests (none currently exercise that
      file directly, so this is a smoke check, not new coverage — documented
      as an accepted scope limit per "Key Insights" above).

## Related Code Files

- Modify: `tests/backend/test_llm.py`
- Modify: `tests/backend/test_bible.py`
- Modify: `tests/backend/helpers.py`
- Verify only (no new test added): `static/js/components/bible_study.js`, `tests/frontend/`

## Implementation Steps

1. In `tests/backend/helpers.py`, add `chat_error_response(status_code, code,
   message="boom")` returning the tuple/shape the test handlers need to
   build an `httpx.Response` with that error body — follow the existing
   `chat_response()` function's signature style.
2. In `test_llm.py`, add a `sleeps: list[float] = []` capture list and
   `monkeypatch.setattr("app.services.llm.asyncio.sleep", fake_sleep)` where
   `fake_sleep` is `async def fake_sleep(seconds): sleeps.append(seconds)`,
   used across the new `Retry-After` tests.
3. Write the numeric-header single-sleep test: a handler returning `429`
   with `headers={"retry-after": "3"}` on the first call and `200` on the
   second; assert `sleeps == [3.0]` and `calls == 2`.
4. Write the no-header-fallback test: a handler returning `429` with no
   `retry-after` header on the first call, `200` on the second; assert
   `len(sleeps) == 1 and sleeps[0] <= 4.0`.
5. Write the `LLMJsonValidationError` type test using `chat_error_response`
   for a 400 with `json_validate_failed`; assert
   `pytest.raises(LLMJsonValidationError)`. Add a second case with an
   unrelated 400 error code and confirm it still raises the base `LLMError`
   (not the subclass) — this is the body `test_4xx_raises_llm_error_without_retry`
   should keep using, confirm it still passes as-is.
6. Extend `test_invalid_json_content_raises` and `test_non_object_json_raises`
   to assert `pytest.raises(LLMJsonValidationError)` instead of the base
   `LLMError`.
7. In `test_bible.py`, change `FlakyLLM`'s raised exception to
   `LLMJsonValidationError(...)` (same message text), confirm the existing
   test at line ~437 passes again.
8. Write the schema-mismatch retry test: mock `complete_json` to return, on
   attempt 1, a dict with an invalid `lexical_exegesis` (e.g. 4 items) and
   otherwise-valid fields; on attempt 2, capture the `system` argument
   passed to the mock and return a fully valid payload. Assert the study is
   created successfully **and** assert the captured attempt-2 `system`
   string contains `"lexical_exegesis"` (or whatever field path Pydantic's
   `exc.errors()` reports for this case — confirm the exact string by
   running the failing case once against real `BibleStudy.model_validate`
   before hardcoding the assertion).
9. Write the exhausted-schema-mismatch test: both `complete_json` calls
   return invalid shapes; assert the resulting error surfaces via the route
   as the friendly Spanish detail, and assert the raw string `input_value`
   does **not** appear in the HTTP response body.
10. Write the `LLMBudgetExceeded` routing test: construct
    `BibleStudyService` with an LLM double whose `complete_json` raises
    `LLMBudgetExceeded`, call the route (or the service directly plus a
    focused route-level test, matching whatever pattern
    `tests/backend/test_routes_*.py` already uses for similar exception-to-
    HTTP mapping checks), assert HTTP 429.
11. Run `pytest tests/backend/test_llm.py tests/backend/test_bible.py -q`,
    then the full suite: `pytest tests/backend -q`.
12. Run `ruff check tests/backend/test_llm.py tests/backend/test_bible.py
    tests/backend/helpers.py` and `mypy app` (matching whatever mypy scope
    the existing test files already are held to — don't newly opt the whole
    `tests/` tree into stricter mypy than it already has).
13. Run `npm test` once as the frontend smoke check described in
    Requirements.

## Todo List

- [x] `chat_error_response` helper added
- [x] 429 single-sleep test (numeric `Retry-After`)
- [x] 429 no-header fallback-to-backoff test
- [x] `LLMJsonValidationError` type-specific test (both the 400 and the two extended 200-body tests)
- [x] `FlakyLLM` fixed to raise the typed exception; existing retry test green again
- [x] Schema-mismatch retry-then-succeed test with a content assertion on the retry prompt
- [x] Schema-mismatch exhausted-retry test asserting no `input_value` leak
- [x] `LLMBudgetExceeded` → 429 routing test
- [x] Full backend suite green, `ruff` + `mypy` clean, `npm test` smoke-checked

## Success Criteria

- Every new test fails against the pre-Phase-1/2 code and passes after the
  corresponding phase's implementation — these are real regression tests,
  not tautologies. In particular, the schema-mismatch retry test must fail
  if `_schema_retry_hint` is changed to return an empty string (proving it
  actually asserts on hint content).
- No new test sleeps for a real multi-second duration; all `Retry-After`
  tests run via monkeypatched sleep.
- Backend test count increases from the 244 baseline (commit `7f4ae49`) by
  at least 8 (one per Requirements bullet above, `FlakyLLM`'s fix doesn't
  count as a new test).

## Risk Assessment

- **Risk:** Monkeypatching `asyncio.sleep` globally could mask a real bug in
  an unrelated concurrent test if `pytest-asyncio` runs tests with shared
  event-loop state. **Mitigation:** scope the monkeypatch to
  `app.services.llm.asyncio.sleep` (the imported reference inside that
  module) via `monkeypatch.setattr`, which `pytest`'s `monkeypatch` fixture
  already undoes after each test.
- **Risk:** Hardcoding the exact Pydantic `exc.errors()` field-path string
  in step 8's assertion could be brittle across a Pydantic version bump.
  **Mitigation:** the step explicitly says to confirm the real string by
  running the failing case once rather than guessing it; if it's especially
  verbose, assert on a substring (`"lexical_exegesis"`) rather than the
  full error message.
- **Risk:** No automated frontend coverage for the `error.status` fix means
  a future refactor of `bible_study.js` could silently reintroduce the
  message-regex pattern. **Mitigation:** accepted and documented (see Key
  Insights) rather than building disproportionate new test infrastructure;
  flagged to the user as an explicit trade-off in this phase's scope.

## Security Considerations

- No production security surface changes in this phase; it is test-only.
  Ensure no test hardcodes a real API key or credential — use the existing
  `api_key="k"` test-double convention already used throughout
  `test_llm.py`.
- The exhausted-schema-mismatch test (step 9) exists specifically to prove
  the security property Phase 1/2 claim: no `input_value` data reaches the
  HTTP response.

## Next Steps

- With this phase complete, re-run `ruff check` and `mypy` across the whole
  `app/` tree once, as a final gate, before considering the plan done.
- Update `CHANGELOG.md` with a new dated entry summarizing the hardening
  (matching the existing changelog's style), since every prior fix in this
  streak got its own changelog entry.
- Raise the pre-existing app-wide log-rotation gap (Phase 3's Risk
  Assessment) with the user as a separate follow-up item.
