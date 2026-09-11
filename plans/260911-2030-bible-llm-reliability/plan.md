---
title: "Bíblia LLM Reliability Hardening"
description: "Close the recurring LLM-failure classes in the Bíblia six-section exegesis pipeline: typed errors, a corrected schema-mismatch retry, structured logging, and the test gaps left by the last hardening streak — redesigned after red-team review rejected the original enforced-deadline mechanism as unsafe."
status: completed
priority: P1
effort: "8-10h"
tags: [backend, frontend, reliability, bugfix, tests]
blockedBy: []
blocks: []
created: 2026-09-11
---

# Bíblia LLM Reliability Hardening

## Overview

The last five commits on `main` (`7f4ae49`, `a450ac8`, `0222eb1`, `daec461`,
`71973f7`) were a reactive hardening streak on the Bíblia cockpit's six-section
exegesis pipeline: a Groq `json_validate_failed` 400, a frontend null-props
render crash, and a 429 rate-limit storm were each fixed as they were hit in
manual testing. This plan continues that streak proactively: it closes the
failure classes the same shape of bug will recur in, removes the duplicated
string-matching used to classify LLM failures (backend *and* frontend), fixes
a real double-sleep bug in the existing 429 handling, adds the logging needed
to diagnose the next failure without reproducing it live, and writes the
regression tests the last three fix commits didn't add for the code they
touched.

Scope is held at "harden the existing pipeline," per the user's explicit
choice — not broadened to new Bíblia features. `app/services/llm.py` and
`app/main.py`'s exception handlers are shared by every cockpit, so Phase 1's
fixes benefit English/Português incidentally; that is not scope creep, it is
the shared client this plan was always going to touch.

## Scope Challenge

- **Existing code found reusable:** `app/services/llm.py` already has
  transient-failure retry with jittered backoff and `Retry-After` honoring;
  `app/services/bible_studies.py` already retries once on a JSON-shape
  failure; `static/js/lib/api.js`'s `ApiError` already carries a structured
  `status` field the frontend wasn't using. This plan extends and corrects
  that machinery — it does not replace it.
- **Requested scope:** Bíblia LLM reliability, hardening the pipeline the
  last five commits touched. Delivered in full across four phases below.
- **Complexity:** ~10 files across 4 phases (see "Files Touched" below); 2
  new exception subclasses; 0 new services. No `--yagni` passed, so nothing
  is deferred — the file count grew from the original draft's ~7 because the
  red-team review below found that draft's frontend and `app/main.py` gaps
  were load-bearing, not optional.
- **Selected mode:** HOLD SCOPE — deliver the full requested hardening scope;
  focus on failure modes, edge cases, and the missing test coverage rather
  than cutting or expanding.

## Red Team Review

### Session — 2026-09-11
**Findings:** 26 raised across 3 reviewers (Security Adversary, Failure Mode
Analyst, Assumption Destroyer), deduplicated to 14 distinct issues.
**Severity breakdown:** 3 Critical, 8 High, 3 Medium.
**Verification tier:** Standard (4 phases) — Fact Checker + Contract Verifier
active on all three reviewers. All file:line citations below were checked by
at least one reviewer; several were checked by all three independently.

| # | Finding | Severity | Disposition | Applied To |
|---|---------|----------|-------------|------------|
| 1 | Phase 1's `isinstance` swap breaks `tests/backend/test_bible.py:437` (`FlakyLLM` raises a bare `LLMError`, never becomes `LLMJsonValidationError`), while three separate plan statements claimed it "passes unmodified" | Critical | Accept | Phase 1, Phase 4 |
| 2 | `llm_study_deadline_seconds` default (45s) is *below* the existing per-call `llm_timeout_seconds` (60s), and the attempt-count arithmetic behind it was wrong (4 attempts, not 3) | Critical | Accept — mechanism removed | Phase 2 |
| 3 | Wrapping the retry loop in `asyncio.timeout`/`wait_for` risks cancelling an in-flight request on the process-wide shared `httpx.AsyncClient` (used by every cockpit + Deepgram + Bible text fetch), with no verified cancellation-safety guarantee | Critical | Accept — mechanism removed | Phase 2 |
| 4 | The frontend detects rate-limiting by regex-matching `429` inside the error *message* text (`bible_study.js:251`), which any of this plan's new friendly-message wording would break, hiding the retry affordance exactly when retrying is correct | High | Accept | Phase 1 |
| 5 | `BibleStudyService` has no access to `Settings`/`get_settings()`; the deadline design silently assumed one | High | Accept — moot, mechanism removed | Phase 2 |
| 6 | `routes_bible.py::create_study` swallows `LLMBudgetExceeded` into a generic 502, so the app's own registered 429 handler (`app/main.py:280-282`) never fires for the Bíblia route | High | Accept | Phase 1 |
| 7 | The global `LLMError` handler (`app/main.py:284-286`) returns `str(exc)` with no truncation, and `_extract_content`/`ValidationError` messages embed full untruncated upstream/model text that can reach the client | High | Accept | Phase 1 |
| 8 | The `json_validate_failed` retry hint ("return valid JSON") cannot fix a schema-*shape* mismatch (right JSON, wrong fields) — that failure needs the actual validation error, not a JSON-syntax reminder | High | Accept | Phase 2 |
| 9 | The 429 path sleeps twice per retried attempt (the `Retry-After` wait, then the unconditional jittered backoff on the next loop iteration) — a real latency bug, not just a documentation gap | High | Accept | Phase 2 |
| 10 | Phase 4's proposed `Retry-After` test asserts a single sleep duration against code that produces two sleeps; the schema-mismatch retry test as specified is tautological (mocks success unconditionally) | High | Accept | Phase 4 |
| 11 | `pyproject.toml` has no `[project]` table — the plan's "check `requires-python`" step reads from a section that doesn't exist | Medium | Accept | Phase 2 (moot — mechanism removed) |
| 12 | New WARNING/ERROR logging on a macOS LaunchAgent deployment writes to an unrotated file (`data/logos-agent.log`) on the same volume as `data/cockpit.db`, and the phase's "1GB Pi" framing is stale against `docs/DEPLOYMENT.md`'s current macOS-primary target | Medium | Accept (scoped down — see Phase 3 Risk Assessment; app-wide log rotation is a pre-existing gap, not solved here) | Phase 3 |
| 13 | The `json_validate_failed`-detection substring fallback classifies based on upstream-controlled response text, which could mis-classify a permanently-failing 400 as retryable | Medium | Accept | Phase 1 |
| 14 | `tests/backend/helpers.py::chat_response()` only builds success payloads; it cannot express a Groq error body, so the new typed-exception test needs a second helper | Medium | Accept | Phase 4 |

### Whole-Plan Consistency Sweep
- Files reread: `plan.md`, `phase-01-typed-error-taxonomy.md`,
  `phase-02-retry-and-resilience-hardening.md`,
  `phase-03-observability-and-logging.md`,
  `phase-04-test-coverage-closure.md`.
- Decision deltas checked: the enforced wall-clock deadline (`asyncio.timeout`
  + `llm_study_deadline_seconds`) was removed entirely, replaced by (a) fixing
  the real 429 double-sleep bug and (b) documenting, not enforcing, the
  resulting worst-case latency; `BibleStudyService`'s constructor is
  therefore **unchanged** by this plan (Finding 5 is moot, not fixed);
  `pyproject.toml`'s Python-version question (Finding 11) is moot for the
  same reason.
- Reconciled stale references: all four phase files were rewritten to remove
  the deadline/settings-wiring language and the `[project] requires-python`
  check; Phase 1 gained the frontend `error.status` fix, the
  `LLMBudgetExceeded` passthrough, and the truncation fix; Phase 2 gained the
  double-sleep fix and the field-path-aware schema hint; Phase 3 gained the
  corrected macOS/Pi framing; Phase 4 gained the corrected `Retry-After`
  assertion, the new error-body test helper, and a non-tautological
  schema-mismatch test.
- Unresolved contradictions: 0.

## Validation Log

### Session — 2026-09-11
**Questions asked:** 3 (within the configured 3-8 range).
**Decisions confirmed:**
1. Log rotation for `data/logos-agent.log` stays out of scope — a
   pre-existing, app-wide gap this plan documents in Phase 3 but does not
   fix, since this plan's own contribution to log volume is bounded by the
   existing retry caps.
2. No new frontend component-test harness for the `bible_study.js`
   `error.status` fix — verified by grep, the existing `ApiError.status`
   guarantee (`tests/frontend/api.test.js:38`), and a manual check; no
   codebase precedent for component-mount tests exists to extend.
3. No enforced wall-clock deadline — Phase 2 ships the 429 double-sleep fix
   and documents worst-case latency; a hard latency SLA is deferred to a
   future spike gated on a verified httpx cancellation-safety check.

All three decisions matched the plan's existing (red-team-revised) design —
no phase file content changed as a result of this interview.

### Whole-Plan Consistency Sweep (post-validation)
- Files reread: `plan.md` and all four `phase-*.md` files.
- Decision deltas checked: 3 (all confirm existing design; none require edits).
- Reconciled stale references: 0 needed.
- Unresolved contradictions: 0.

## Goals

| # | Goal | Priority |
|---|------|----------|
| 1 | Replace string-matched LLM failure classification with typed exceptions — backend *and* frontend | P1 |
| 2 | Retry the schema-valid-but-wrong-shape failure class with a hint that can actually fix it (field paths, not a JSON-syntax reminder) | P1 |
| 3 | Fix the real 429 double-sleep bug and document (not artificially enforce) the resulting worst-case latency | P2 |
| 4 | Log every retried/exhausted LLM failure with enough context to diagnose without reproducing | P1 |
| 5 | Add the regression tests the last three fix commits left uncovered, with assertions that can actually fail | P1 |

## Phases

| # | Phase | Status |
|---|-------|--------|
| 1 | [Typed LLM Error Taxonomy](./phase-01-typed-error-taxonomy.md) | Completed |
| 2 | [Retry and Resilience Hardening](./phase-02-retry-and-resilience-hardening.md) | Completed |
| 3 | [Observability and Logging](./phase-03-observability-and-logging.md) | Completed |
| 4 | [Test Coverage Closure](./phase-04-test-coverage-closure.md) | Completed |

## Files Touched

- `app/services/llm.py` — typed exceptions, structural+fallback detection, double-sleep fix, new logger (Phases 1-3)
- `app/services/bible_studies.py` — schema-mismatch retry with field-path hint, logging (Phases 2-3)
- `app/api/routes_bible.py` — `LLMBudgetExceeded`/`LLMSchemaMismatchError` routing (Phases 1-2)
- `app/main.py` — global `LLMError` handler truncation (Phase 1)
- `app/core/config.py` — no changes (deadline setting was rejected; noted here so it isn't re-added by mistake)
- `static/js/components/bible_study.js` — `error.status`-based classification instead of message regex (Phase 1)
- `docs/DEPLOYMENT.md` — corrected log-location docs, documented worst-case latency (Phases 2-3)
- `tests/backend/test_llm.py` — new typed-exception, double-sleep, and `Retry-After` tests (Phase 4)
- `tests/backend/test_bible.py` — corrected `FlakyLLM`, new schema-mismatch and budget tests (Phase 4)
- `tests/backend/helpers.py` — new error-body mock helper (Phase 4)
- `tests/frontend/` — a small test for the `error.status` fix if a suitable existing test file covers `bible_study.js`-adjacent logic (Phase 4; see that phase for the exact scope decision)

## Success Criteria

- [x] No caller of `app/services/llm.py`, in either Python or JavaScript, classifies a failure by substring-matching an error message; classification is by exception type (backend) or `error.status` (frontend). Verified: `grep -rn "json_validate_failed" app/` returns one match (in `llm.py` itself); `bible_study.js:251` uses `error.status === 429`.
- [x] A schema-valid JSON response that fails `BibleStudy.model_validate` triggers one corrective retry whose hint states the actual failing field paths, not a generic "return valid JSON" reminder. Verified by `test_study_retries_schema_mismatch_with_field_path_hint` (`tests/backend/test_bible.py`).
- [x] A 429 response sleeps for exactly one duration per retried attempt (the `Retry-After` value when present and honorable, otherwise the jittered backoff) — never both. Verified by `test_429_with_retry_after_sleeps_exactly_once` (`tests/backend/test_llm.py`).
- [x] `LLMBudgetExceeded` on `/api/bible/study` returns 429, matching every other LLM route in the app. Verified by `test_study_route_maps_budget_exceeded_to_429`.
- [x] The global `LLMError` exception handler never returns more than 200 characters of upstream/model text to the client. Verified: `app/main.py:284-288` slices `str(exc)[:200]`.
- [x] `app/services/bible_studies.py`'s existing `logger` (currently imported, unused) and a new logger in `app/services/llm.py` emit a log line for every retried attempt and every exhausted-retry failure. Verified: `grep -c "logger\."` returns 4 (bible_studies.py) and 5 (llm.py); both were 0 before this plan.
- [x] `tests/backend/test_llm.py` covers `_retry_after_seconds` and the corrected single-sleep 429 path; `tests/backend/test_bible.py` covers the schema-mismatch retry with an assertion that can fail (checks the retry prompt contains the specific validation error, not just that a second call happened). Verified: both landed, plus a follow-up commit (`fb7f7a0`) closed a direct-coverage gap on `_retry_after_seconds` itself.
- [x] `ruff check` and `mypy` are clean; the full backend suite passes; `npm test` (frontend) passes. Independently re-verified at close-out: 268/268 backend tests, `ruff check` clean, `mypy app` clean (70 files), 64/64 frontend tests.

## Implementation Notes (post-close)

Implemented across 6 commits on `main`: `be12662` (Phase 1), `6be2264`
(Phase 2), `0599147` (Phase 3), `d034760` + `fb7f7a0` (Phase 4, the second
commit closing a direct-coverage gap on `_retry_after_seconds` the first one
left), and `afc4245` — a size-capped `RotatingFileHandler`
(`app/core/logging_setup.py`) for `data/logos.log`, addressing the
log-rotation gap Phase 3's Risk Assessment flagged as an explicit follow-up
rather than in-scope. Backend test count grew 244 → 268. Every commit
message records its own `ruff`/`mypy`/test verification; this session
independently re-ran all three gates and confirmed the counts match.

## Dependencies

- None outside this repository. All changes are internal to the FastAPI backend, its frontend, and their test suites; no new external services, credentials, or configuration settings (the originally proposed `LLM_STUDY_DEADLINE_SECONDS` setting was rejected in red-team review — see Finding 2/3 above).

<!-- slug: bible-llm-reliability -->
