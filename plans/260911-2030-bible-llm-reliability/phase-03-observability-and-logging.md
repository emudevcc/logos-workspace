---
phase: 3
title: "Observability and Logging"
status: pending
priority: P1
effort: "1.5h"
dependencies: [1, 2]
---

# Phase 3: Observability and Logging

## Goal

Make every retried and exhausted LLM failure in the Bíblia pipeline visible
in the process log, using the logger `bible_studies.py` already imports but
never calls, so the next failure can be diagnosed from the deployed log
without reproducing it live.

<!-- Updated: Red Team Review Session 2026-09-11 — the original phase framed
the deployment as "a Raspberry Pi 3B (1GB RAM)". docs/DEPLOYMENT.md:3-4
documents macOS (Apple Silicon) as the current primary target, with the
Pi 3B "still supported via deploy.sh/systemd" as a secondary path. This
phase now covers both correctly, and the log-rotation risk raised in review
is scoped down to what this phase actually controls rather than building
app-wide logging infrastructure — see Risk Assessment. -->

## Context Links

- `app/services/bible_studies.py:26` — `logger = logging.getLogger(__name__)`
  is declared but has zero call sites in the current file; every retry and
  every failure in `_build_report` is currently silent until it reaches the
  client as an HTTP response.
- `app/services/llm.py` — has no module logger at all today; `_post_completions`
  swallows `httpx.TransportError` into `last_error` and retries without a
  trace of how many times or why.
- `grep -rn "basicConfig\|RotatingFileHandler\|dictConfig" app/` — no match:
  the app configures no logging handler of its own anywhere. Log records
  from `app.services.*` loggers propagate to the root logger, which (with no
  handler configured) uses Python's `logging.lastResort` — a plain
  `StreamHandler` to `stderr` for `WARNING` and above.
- `deploy/macos/install-logos-agent.sh` — the macOS LaunchAgent redirects
  both stdout and stderr to `data/logos-agent.log`, the **same `data/`
  directory** that holds `data/cockpit.db` (per `app/core/config.py`'s
  `db_path` default) — and nothing rotates that file.
- `docs/DEPLOYMENT.md:3-4` — "Target: macOS (Apple Silicon), Python 3.11+.
  The original Raspberry Pi 3B target is still supported via `deploy.sh` /
  systemd." `docs/DEPLOYMENT.md:202` already documents `journalctl -u
  english-cockpit -f` for that systemd path — journald handles its own log
  retention, so the Pi/systemd path is not at the same disk-fill risk as the
  macOS LaunchAgent's unrotated file.

## Key Insights

- This is a single-worker, single-machine deployment either way (README:
  "a single async uvicorn worker") with no external log aggregation — the
  plain process log *is* the observability story on both supported targets.
  An unused logger import is a real, cheap-to-close gap, not a style nit.
- Because no `logging.basicConfig`/handler exists, adding `logger.warning`/
  `logger.error` calls "just works" on both deployment paths without any new
  configuration: on macOS they land in `data/logos-agent.log` via the
  LaunchAgent's stderr redirect; on the Pi/systemd path they land in
  `journalctl`. This phase does not need to add or change any logging
  configuration to be effective.
- Logging must stay cheap and bounded: never log the full passage text or
  full LLM response body — truncate exactly as Phase 1's `_truncate()`
  helper already does for the exception messages themselves; reuse it here
  rather than re-truncating ad hoc.
- Never log the `Authorization` header or the raw API key.
  `_post_completions` builds `headers` locally and never logs them today;
  keep it that way.

## Requirements

- [x] Add a module-level `logger = logging.getLogger(__name__)` to
      `app/services/llm.py`.
- [x] In `_post_completions`, log at `WARNING` on each retried attempt
      (transient transport error, 429, or 5xx) with the attempt number,
      status code (or exception type for transport errors), and which sleep
      path fired (backoff, `Retry-After`, or neither after the Phase 2 fix) —
      no request/response body.
- [x] In `_post_completions`, log at `WARNING` specifically when the
      substring-fallback JSON-failure detection fires (Phase 1's
      requirement), distinct from the structural `error.code` match, so an
      unexpected upstream shape is visible.
- [x] In `_post_completions`, log at `ERROR` when retries are exhausted,
      including the total attempt count and the final error (truncated via
      `_truncate`), before raising.
- [x] In `bible_studies.py::_build_report`, use the existing `logger` to log
      at `WARNING` when attempt 0 fails and a retry is about to happen
      (include which typed exception triggered it — `LLMJsonValidationError`
      or `LLMSchemaMismatchError` — and, for the latter, the field paths from
      Phase 2's `_schema_retry_hint` input), and at `ERROR` when both
      attempts are exhausted, before raising.
- [x] All new log calls truncate any included upstream/model text via the
      Phase 1 `_truncate()` helper.
- [x] Add a short "Diagnosing a failed Bíblia study" subsection to
      `docs/DEPLOYMENT.md` that names **both** log locations correctly: the
      LaunchAgent's `data/logos-agent.log` on macOS, and `journalctl -u
      english-cockpit -f` on the Pi/systemd path (matching the existing
      line at `docs/DEPLOYMENT.md:202`, don't duplicate or contradict it).

## Architecture

```
llm.py._post_completions()
  on retry:              logger.warning("llm retry attempt=%d status=%s sleep=%s", ...)
  on fallback detection: logger.warning("llm json-failure fallback-detected body=%s", _truncate(...))
  on exhausted:          logger.error("llm retries exhausted attempts=%d last_error=%s", ...)

bible_studies.py._build_report()
  on attempt-0 failure -> retry:  logger.warning("bible study retry reason=%s ref=%s", type(last_error).__name__, ref.display)
  on final failure:               logger.error("bible study failed reason=%s ref=%s", type(last_error).__name__, ref.display)
```

## Related Code Files

- Modify: `app/services/llm.py`
- Modify: `app/services/bible_studies.py`
- Modify: `docs/DEPLOYMENT.md`

## Implementation Steps

1. Add `import logging` and `logger = logging.getLogger(__name__)` near the
   top of `app/services/llm.py`, next to the existing imports.
2. In `_post_completions`'s retry branches, add `logger.warning(...)` calls
   as specified above, including the fallback-detection case from Phase 1.
3. At the final `raise LLMError(f"LLM request failed after ...")`, add a
   `logger.error(...)` call immediately before it.
4. In `bible_studies.py::_build_report`, add a `logger.warning(...)` call in
   each `if attempt == 0: continue` branch (both the `LLMJsonValidationError`
   and `LLMSchemaMismatchError` cases from Phase 2), and a `logger.error(...)`
   call right before each terminal `raise`. Include `ref.display` (the
   passage reference) so a failure can be correlated to what was being
   studied, but never the full `passage_text` or the full LLM `raw` payload.
5. Add the "Diagnosing a failed Bíblia study" subsection to
   `docs/DEPLOYMENT.md`, correcting the deployment-path-specific log
   location for each of the two supported targets.
6. Run `ruff check app/services/llm.py app/services/bible_studies.py`.
7. Manually trigger one retried failure locally (e.g. temporarily point
   `LLM_BASE_URL` at a handler that 500s once) and confirm the WARNING line
   appears with the expected fields, then confirm a real study still
   succeeds end-to-end.

## Todo List

- [x] Logger added to `llm.py`
- [x] WARNING on every retried attempt and every fallback-detection event (both files)
- [x] ERROR on every exhausted/final failure (both files)
- [x] All logged text truncated via the shared `_truncate()` helper, no secrets, no full passage text
- [x] `docs/DEPLOYMENT.md` diagnosing subsection names both deployment paths correctly
- [x] Manual retry-and-recover smoke test confirms the log lines

## Success Criteria

- `grep -n "logger\." app/services/bible_studies.py` returns at least two
  matches (was zero before this phase).
- `grep -n "logger\." app/services/llm.py` returns at least two matches (was
  zero before this phase — no logger existed at all).
- A manually triggered transient failure that recovers produces exactly one
  WARNING line and zero ERROR lines; a failure that exhausts all retries
  produces exactly one ERROR line.
- No log line in either file contains the `Authorization` header value, the
  full passage text, or an untruncated upstream response body.
- `docs/DEPLOYMENT.md` correctly names `data/logos-agent.log` for the macOS
  target and `journalctl -u english-cockpit -f` for the Pi/systemd target —
  it does not claim one is the only log location for both.

## Risk Assessment

- **Risk (real, scoped down — not solved here):** the macOS LaunchAgent's
  `data/logos-agent.log` has no rotation and shares a volume with
  `data/cockpit.db`; this phase adds a bounded number of new log lines per
  request (at most ~6, gated by the existing retry caps — 4 network attempts
  and 2 business attempts, unchanged by this plan), which does not turn an
  already-bounded-by-rate-limiting request volume (30/min per IP,
  `app/core/config.py:54`) into an unbounded one. The pre-existing lack of
  log rotation is a real operational gap that predates this plan and affects
  every cockpit's logging, not just Bíblia's — fixing it (a
  `RotatingFileHandler` or an OS-level `newsyslog`/`logrotate` entry) is
  explicitly **out of scope** for this plan and should be tracked as a
  separate, app-wide follow-up rather than solved piecemeal here.
- **Risk:** Including `ref.display` in logs could be considered logging
  user activity (which passages someone is studying). **Mitigation:** this
  is a single-user personal deployment (per `docs/DEPLOYMENT.md`'s
  macOS-LaunchAgent/Pi-kiosk framing, not a multi-tenant service) — flagged
  here for visibility; no change needed unless the deployment model changes.

## Security Considerations

- Never log the `LLM_API_KEY`, the `Authorization` header, or an untruncated
  upstream response body — enforced by reusing Phase 1's `_truncate()`
  helper rather than re-truncating ad hoc.
- Log level choices (`WARNING`/`ERROR` only, no `DEBUG` payload dumps) keep
  sensitive theological-study content out of the log by default.

## Next Steps

- Phase 4 doesn't test log output directly (logging is observability, not a
  contract), but it does test the exception types these log calls key off
  of, which indirectly protects the log call sites from silently going dead
  if an exception type is renamed later.
- The pre-existing log-rotation gap noted above is worth raising with the
  user as a separate, app-wide follow-up item once this plan ships.
