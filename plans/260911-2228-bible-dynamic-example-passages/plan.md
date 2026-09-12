---
title: "Dynamic Bíblia Example-Passage Chips"
description: "Replace the Bíblia cockpit's 6 hardcoded example-passage chips with LLM-generated suggestions on each load, mirroring the existing Word-of-Day generator's shape (LLM when configured, graceful fallback to the current curated list otherwise)."
status: completed
priority: P2
effort: "2.5-3.5h"
tags: [backend, frontend, feature, bible]
blockedBy: []
blocks: []
created: 2026-09-11
---

# Dynamic Bíblia Example-Passage Chips

## Overview

Today `static/js/components/bible_study.js`'s `I18N[lang].examples` is a
fixed array of 6 passage references per language (es/en/pt), always the
same passages in the same order, shown as clickable chips above the study
input. You asked for these to be dynamic, and picked **LLM-generated each
load** — the same shape as the English cockpit's Word-of-Day card
(`app/services/word_of_day.py`'s `WordOfDayGenerator`): generate a fresh
item via the shared LLM when configured, fall back to a fixed pool when it
isn't or when generation fails, no user-visible error either way.

This plan adds a `BiblePassageSuggester` service (new file, mirrors
`WordOfDayGenerator`'s structure) that asks the LLM for a handful of
well-known passage references appropriate for a 5–15 verse exegetical study,
validates each one through the *existing* reference parser before it's ever
shown to the user (a suggestion the app itself can't parse is worse than no
suggestion), and keeps a small anti-repeat window so reloads don't keep
serving the same reference. A new `GET /api/bible/example-passages` endpoint
serves it. The frontend fetches this on mount and on language change, using
the current hardcoded array as the local fallback it already has — no new
curated data needs to live on the backend.

## Scope Challenge

- **Existing code found reusable:** `app/services/word_of_day.py`'s
  `WordOfDayGenerator` is the exact pattern to mirror (LLM-generate with a
  recent-window anti-repeat dedupe, `LLMError` on failure, caller falls back
  to a fixed pool) — this plan does not invent a new generation pattern.
  `app/services/bible_parser.py::parse_reference` already validates any
  reference string against the real 66-book alias table; reusing it to
  filter LLM suggestions is new wiring, not new logic. The frontend's
  existing `I18N[lang].examples` arrays become the fallback pool as-is — no
  backend duplication of curated data.
- **Requested scope:** make the example-passage list dynamic via
  LLM-generation-per-load, confirmed via the earlier clarifying question.
  Delivered in full across two phases below.
- **Complexity:** 5 files across 2 phases (`app/services/bible_examples.py`
  new, `app/main.py`, `app/api/routes_bible.py`,
  `static/js/components/bible_study.js`, plus their test files); 1 new
  service class, 0 new schemas (the endpoint returns a plain `list[str]`,
  matching `GET /api/bible/books`'s existing simplicity). No `--yagni`
  passed; nothing deferred.
- **Selected mode:** Fast — small, well-scoped feature with a direct
  precedent to mirror; no unfamiliar tech or architecture. No red-team/
  validate loop (not required in Fast mode); this plan was still grounded
  against the actual codebase (file:line citations below) rather than
  assumed.

## Key Design Decision: Validate Every Suggestion Before Showing It

Word-of-Day's LLM output only has to be *non-empty* to be useful — a vague
or slightly-off vocabulary item is harmless. A **passage reference** is
different: if the LLM hallucinates a book name, a chapter that doesn't
exist, or malformed syntax, clicking that chip either 422s or (worse) sends
a slightly-wrong reference into the exact LLM pipeline this workspace just
spent a whole prior plan (`plans/260911-2030-bible-llm-reliability/`,
archived) hardening. So every suggested string **must** round-trip through
`parse_reference()` (`app/services/bible_parser.py:51`) before it's returned
— anything that raises `BibleReferenceError` is dropped silently, never
shown to the user. This is the one place this plan diverges from
Word-of-Day's validation depth, for a good reason grounded in the previous
plan's findings, not a stylistic preference.

## Goals

| # | Goal | Priority |
|---|------|----------|
| 1 | Add `BiblePassageSuggester`, mirroring `WordOfDayGenerator`'s LLM-generate-with-anti-repeat shape | P1 |
| 2 | Validate every suggestion through the real reference parser before it's servable | P1 |
| 3 | Serve it via a new endpoint that never surfaces an error to the client (LLM failure → empty list, frontend already has a fallback) | P1 |
| 4 | Wire the frontend to fetch fresh chips on mount and on language change, falling back to the current hardcoded array | P2 |

## Phases

| # | Phase | Status |
|---|-------|--------|
| 1 | [Backend Passage Suggester](./phase-01-backend-passage-suggester.md) | Completed |
| 2 | [Frontend Dynamic Chips](./phase-02-frontend-dynamic-chips.md) | Completed |

## Files Touched

- `app/services/bible_examples.py` — new: `BiblePassageSuggester` (Phase 1)
- `app/main.py` — wire `app.state.bible_examples` next to `app.state.word_of_day`/`app.state.bible_studies` (Phase 1)
- `app/api/routes_bible.py` — new `GET /api/bible/example-passages` route (Phase 1)
- `tests/backend/test_bible_examples.py` — new (Phase 1)
- `static/js/components/bible_study.js` — fetch-and-fallback wiring for `renderChips` (Phase 2)
- `docs/API.md` — document the new endpoint (Phase 2)

## Success Criteria

- [x] `BiblePassageSuggester.suggest()` never returns a string that
      `parse_reference()` rejects. Verified by test and by the mutation
      check recorded in `1f00efd`'s commit message. One known limitation
      (see Implementation Notes): `parse_reference` itself only enforces
      lower bounds, not per-book chapter/verse ceilings, so an
      out-of-range-but-syntactically-valid reference (e.g. "Juan 99:1") can
      still pass — this is pre-existing parser behavior this plan
      deliberately didn't expand scope to fix (matches the plan's own Risk
      Assessment).
- [x] `GET /api/bible/example-passages?language=es|en|pt` returns 200 with a
      (possibly empty) JSON array in every case. Verified: `grep -n
      "raise\|HTTPException" app/api/routes_bible.py` shows no raise inside
      this route.
- [x] Two consecutive calls to `BiblePassageSuggester.suggest()` don't return
      an identical list. Verified by a mutation-checked test (forcing the
      avoid-hint to `""` fails the assertion, per `1f00efd`).
- [x] The chips render correctly with zero backend changes rolled back —
      `loadChips()` only replaces the fallback on a non-empty array and
      never clears it on failure; verified directly against four scenarios
      per `e0558ba`'s commit message (success, stale-response, empty array,
      rejected request).
- [x] `ruff check`, `mypy app`, the backend suite, and `npm test` all pass.
      Independently re-verified at close-out: 297/297 backend tests
      (298 minus the 8 added later by the favorites plan — see note below),
      `ruff check` clean, `mypy app` clean (71 files), 64/64 frontend tests.

## Implementation Notes (post-close)

Implemented across 3 commits: `1f00efd` (Phase 1: `BiblePassageSuggester` +
endpoint, 20 new tests), `e0558ba` (Phase 2: frontend fetch/fallback/stale-
guard wiring), and `a23705e` — a same-day follow-up that documented rather
than fixed a pre-existing gap: `parse_reference` has no per-book chapter/
verse ceiling, so an occasionally out-of-range reference can be suggested.
This was flagged as an accepted, out-of-scope limitation in Phase 1's own
Risk Assessment; the follow-up commit added a test pinning the behavior and
a `CHANGELOG.md` known-gap entry rather than building the 66-book
chapter-count table a real fix would need. One implementation refinement
beyond the plan's literal spec: `_SuggestedPassages` declares `passages:
list[Any]` rather than `list[str]`, so one non-string entry in an otherwise
good LLM response doesn't make Pydantic discard the whole list — a sensible
robustness improvement the plan didn't specify but is consistent with its
intent. Backend test count grew 268 → 289 across these three commits (the
subsequent favorites plan added 8 more, to 297). Every commit's own
`ruff`/`mypy`/test verification was independently re-confirmed at close-out.

## Dependencies

- None outside this repository. Reuses the existing shared LLM client and
  budget/rate-limiting; no new external services or settings.

<!-- slug: bible-dynamic-example-passages -->
