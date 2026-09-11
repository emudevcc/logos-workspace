---
title: "Bíblia LLM reliability hardening: closing a reactive bug-fix streak proactively"
date: 2026-09-11
summary: "Hardened the Bíblia exegesis pipeline's LLM error handling (typed exceptions, schema-mismatch retry, 429 double-sleep fix, logging, tests); red team killed an enforced wall-clock deadline over shared-httpx-client cancellation risk."
---

# Bíblia LLM reliability hardening: closing a reactive bug-fix streak proactively

**Date**: 2026-09-11 20:30
**Severity**: Medium
**Component**: Bíblia cockpit — LLM exegesis pipeline (`app/services/llm.py`, `app/services/bible_studies.py`, `app/api/routes_bible.py`, `app/main.py`, `static/js/components/bible_study.js`)
**Status**: Resolved

## What Happened

The five commits before this plan (`7f4ae49`, `a450ac8`, `0222eb1`, `daec461`,
`71973f7`) were a reactive fix-it-when-it-breaks streak on the Bíblia
six-section exegesis pipeline: a Groq `json_validate_failed` 400 blew up in
manual testing, then a frontend null-props crash, then a 429 rate-limit
storm — each patched only after being hit live. This plan (`plans/260911-2030-bible-llm-reliability/`)
was the deliberate follow-up: stop waiting for the next failure to teach us
what's fragile, and close the failure *classes* instead of the individual
symptoms. Scope was explicitly held to "harden what exists" — no new Bíblia
features, per the user's own instruction.

## The Brutal Truth

Three separate places — `bible_studies.py`, `routes_bible.py`, and
`bible_study.js` — were all independently regex/substring-matching the same
free-text LLM error message to decide what to do next. That's not
resilience, that's three copies of the same guess, and any one wording
change anywhere in the error path could silently break retry logic or hide
the rate-limit UI exactly when a user needed the retry button. Worse, a real
shipped bug had gone unnoticed: the 429 handler was sleeping *twice* per
retried attempt (the `Retry-After` wait, then the unconditional jittered
backoff on the next loop iteration) — a latency bug nobody had measured
because nothing was timing it.

## Technical Details

The original draft proposed enforcing a hard wall-clock deadline
(`asyncio.timeout`/`wait_for` + a new `llm_study_deadline_seconds` setting,
default 45s) around the retry loop. Red team review (3 reviewers, 26 raw
findings → 14 deduped, 3 Critical) killed it outright: `llm.py`'s
`httpx.AsyncClient` is a **process-wide shared client** used by every
cockpit (English, Português, Bíblia) plus Deepgram and the Bible-text
fetcher, and there was no verified guarantee that cancelling a coroutine
mid-`await` on that shared client wouldn't corrupt or leak connection-pool
state for an unrelated in-flight request from a different cockpit. On top of
that, the proposed 45s default was *below* the existing per-call
`llm_timeout_seconds` (60s) — the mechanism would have fired before its own
guarded call could even legitimately time out, and the attempt-count math
behind it was wrong (4 network attempts, not 3, given `llm_max_retries=3`).

## What We Tried

- Considered enforcing the deadline as designed — rejected in red-team review
  (Findings #2, #3) as an unverified cancellation risk on shared
  infrastructure, not just a config bug.
- Landed instead: `LLMJsonValidationError` and `LLMSchemaMismatchError` typed
  exceptions replacing all three copies of the substring-matching (Phase 1);
  a field-path-aware retry hint built from Pydantic's `exc.errors()`
  `(loc, msg)` pairs — never `input` — for the "right JSON, wrong shape"
  failure class that previously got zero retries (Phase 2); the actual
  429-double-sleep fix via an `honored_retry_after` gate, plus documentation
  (not enforcement) of the resulting worst-case latency in
  `docs/DEPLOYMENT.md` (Phase 2); WARNING/ERROR logging on every retried and
  exhausted attempt in both `llm.py` and `bible_studies.py`, truncated via a
  shared `_truncate()` helper so nothing sensitive or unbounded lands in the
  log (Phase 3); and the regression tests the last three fix commits never
  wrote, including a corrected `Retry-After` test (`sleeps == [3.0]`, not
  `3.0 in sleeps`) and a non-tautological schema-mismatch test that asserts
  the retry prompt actually contains the failing field path (Phase 4).

## Root Cause Analysis

The prior streak fixed each bug where it was found — 400, then null-render,
then 429 — without asking what *shape* of bug those were, so the same shape
(unstructured error text driving branching logic in three languages/layers)
kept recurring. The double-sleep bug specifically existed because nobody had
instrumented the retry path with logging or a test that could see the timing
— the original draft's own replacement test would have been tautological
too (`3.0 in sleeps` passes whether there's one sleep or two), which the
red team caught before it shipped a test that couldn't fail.

## Lessons Learned

1. Don't reach for `asyncio.timeout`/`wait_for` around a shared long-lived
   client without first verifying cancellation safety for every other
   caller of that client — a spike, not an assumption. This plan explicitly
   defers a hard latency SLA to that future spike (see Phase 2's Risk
   Assessment) instead of shipping something unverified.
2. When three places derive the same decision from the same string, that's
   not defense in depth, it's a single point of failure with three names.
   Typed exceptions and `ApiError.status` (which the frontend already had
   and wasn't using) were sitting right there.
3. A regression test that can't fail (mocking unconditional success
   regardless of the retry hint's content, or asserting `x in list` instead
   of `list == [x]`) is worse than no test — it's false confidence with a
   green checkmark on it.
4. Fixing a config-value symptom (lowering a deadline number) instead of the
   double-sleep bug behind it would have shipped a self-defeating default
   (45s deadline under a 60s per-call timeout). Read the arithmetic before
   trusting the plan.

## Next Steps

Shipped as 6 commits on `main`: `be12662` (Phase 1 — typed exceptions,
truncation, `LLMBudgetExceeded` passthrough), `6be2264` (Phase 2 — 429
double-sleep fix, schema-mismatch retry), `0599147` (Phase 3 — logging),
`d034760` + `fb7f7a0` (Phase 4 — tests, the second commit closing a direct
`_retry_after_seconds` coverage gap the first left open), and `afc4245` — a
size-capped `RotatingFileHandler` for `data/logos.log`
(`app/core/logging_setup.py`), which went beyond this plan's original scope
to address the log-rotation gap Phase 3's Risk Assessment had explicitly
flagged as a follow-up rather than in-scope (the macOS LaunchAgent's
unrotated `data/logos-agent.log` sharing a volume with `data/cockpit.db`).
Verified impact: backend test count grew 244 → 268, `ruff check` and `mypy
app` (70 files) both clean, 64/64 frontend tests passing — independently
re-verified at close-out, not just trusted from commit messages. Owner:
Esteban. No further action required on this plan; the deferred hard-latency
SLA spike (cancellation-safety verification on the shared `httpx.AsyncClient`)
remains an open, explicitly-not-yet-scheduled follow-up if a real need for
one ever surfaces.

> Historical work record — not durable authority. Prefer docs/specs/ADRs for current decisions.
