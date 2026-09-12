---
title: "Favorite Bíblia Studies"
description: "Add a persisted favorite flag to saved Bíblia studies, a toggle in the existing history list, and a new Favoritos view — mirroring the existing study-history feature, scoped to favorited studies only."
status: completed
priority: P2
effort: "3-4h"
tags: [backend, frontend, feature, bible]
blockedBy: []
blocks: []
created: 2026-09-11
---

# Favorite Bíblia Studies

## Overview

The Bíblia cockpit's history (`bible_history.js` + `GET/DELETE
/api/bible/studies[/{id}]`) lists every saved study — one row per generated
report (re-studying a passage or switching its language creates a new row).
You want something similar, scoped to studies you've marked as favorites.

Per your decisions: a favorite is a flag on a specific saved study row (not
a passage-independent bookmark) — mirroring history exactly, so favoriting
the same passage in two languages gives you two independent favorite
entries, each a real reopenable report. You can star/unstar a study from
the existing history list, and a new **Favoritos** nav tab shows only the
starred ones, registered the same way `bible-history` already is.

Because the history list and the new favorites list are the same UI
(load a list, open a study, delete a study) filtered differently, this plan
extracts the shared logic into one small library module both components
call, rather than forking `bible_history.js` into two near-duplicate files.

## Scope Challenge

- **Existing code found reusable:** `app/services/bible_studies.py`'s
  `list_studies`/`get_study`/`delete_study` (lines 330-368), the versioned
  SQLite migration system in `app/core/db.py` (currently at schema v5, one
  `ALTER TABLE` away from v6), `StudySummary`/`StudyRecord` schemas
  (`app/schemas/bible.py:94-104`, `StudyRecord` already inherits from
  `StudySummary`), and the `data-view`/`data-cockpit` nav registration
  pattern already used for `bible-history` (`templates/index.html:49`,
  `static/js/main.js:16,61`). This plan extends all of these — it does not
  replace or fork them.
- **Requested scope:** a favorites list "similar to" history, scoped to
  favorited studies, with a star toggle in history and a new Favoritos tab
  — confirmed via the two clarifying questions above. Delivered in full
  across two phases below.
- **Complexity:** 11 files touched across 2 phases (backend: db migration,
  2 schema changes, 2 service methods, 2 route changes/additions, 1 test
  file; frontend: 1 new shared lib module, 1 modified component, 1 new
  component, main.js registration, index.html nav wiring; plus one docs
  file). This is over the informal "8 files" scope-challenge threshold, but
  every file is load-bearing for the requested feature (a persisted flag +
  a toggle endpoint + a filtered list + its nav entry + tests + docs) — none
  are additions beyond what was asked, and the frontend refactor (extracting
  a shared list module) reduces net new code rather than adding an unrelated
  abstraction. No `--yagni` passed; nothing deferred.
- **Selected mode:** Fast — closely mirrors an existing, fully-scouted
  feature (history) with a proven pattern to extend, not unfamiliar
  territory. No red-team/validate loop (not required in Fast mode), but
  every claim below is grounded in the actual current file:line state
  checked during this session, not assumed from memory of the earlier
  history-feature work.

## Goals

| # | Goal | Priority |
|---|------|----------|
| 1 | Persist an `is_favorite` flag per saved study (schema v6 migration) | P1 |
| 2 | Add a toggle endpoint and a favorites-only filter to the existing list endpoint | P1 |
| 3 | Star/unstar toggle in the existing history list | P1 |
| 4 | New "Favoritos" nav tab showing only favorited studies, via shared list logic (not a forked copy of history.js) | P1 |

## Phases

| # | Phase | Status |
|---|-------|--------|
| 1 | [Backend Favorite Flag](./phase-01-backend-favorite-flag.md) | Completed |
| 2 | [Frontend Favorites View](./phase-02-frontend-favorites-view.md) | Completed |

## Files Touched

- `app/core/db.py` — schema v6 migration: `is_favorite` column on `studies` (Phase 1)
- `app/schemas/bible.py` — `StudySummary.is_favorite`, new `FavoriteRequest` (Phase 1)
- `app/services/bible_studies.py` — `list_studies(favorites_only=False)`, `get_study`/row mapping, new `set_favorite()` (Phase 1)
- `app/api/routes_bible.py` — `favorites_only` query param, new `POST /studies/{id}/favorite` (Phase 1)
- `tests/backend/test_bible.py` — coverage for the above (Phase 1)
- `static/js/lib/bible_saved_list.js` — new: shared list/detail/delete/star logic (Phase 2)
- `static/js/components/bible_history.js` — refactored onto the shared module, gains the star toggle (Phase 2)
- `static/js/components/bible_favorites.js` — new: thin wrapper over the shared module, favorites-only (Phase 2)
- `static/js/main.js` — register the `bible-favorites` view + icon (Phase 2)
- `templates/index.html` — new nav button + `app-view` section for Favoritos (Phase 2)
- `docs/API.md` — document the new/changed endpoints (Phase 2)

## Success Criteria

- [x] Toggling favorite on a study in the history list persists across a
      page reload. Verified: the v6 migration was exercised directly
      (`PRAGMA user_version` reads 6, column exists on a fresh DB) and two
      mutation checks confirmed the SELECT/filter tests actually bite
      (dropping `is_favorite` from the SELECT raises `IndexError`; ignoring
      `favorites_only` fails the empty-list assertion), per `3200d19`.
- [x] `GET /api/bible/studies?favorites_only=true` returns only favorited
      studies, in the same order/shape as the unfiltered list.
- [x] The Favoritos tab shows an empty state (not an error) when nothing is
      favorited yet — confirmed distinct from history's message ("Todavía
      no tienes estudios favoritos." vs. "Todavía no hay estudios
      guardados."), proving the parameterization genuinely varies per call
      site rather than being hardcoded once.
- [x] `bible_history.js` and `bible_favorites.js` share list/open/delete/star
      logic through `bible_saved_list.js`. Verified: both components are
      now 13-line wrappers (`wc -l` confirms); the row-building, detail
      view, and delete code exists in exactly one file.
- [x] `ruff check`, `mypy app`, the backend suite, and `npm test` all pass.
      Independently re-verified at close-out: 297/297 backend tests,
      `ruff check` clean, `mypy app` clean (71 files), 64/64 frontend tests.

## Implementation Notes (post-close)

Implemented across 2 commits: `3200d19` (Phase 1: migration, schema,
service, routes, 8 new tests) and `808cf33` (Phase 2: the shared
`bible_saved_list.js` extraction, both thin wrapper components, nav/main.js
registration, docs). Two implementation notes worth recording:

- Phase 1 found that Pydantic's lax validation mode coerces strings like
  `"yes"`/`"true"` to a bool, so `FavoriteRequest`'s malformed-body test
  uses a non-coercible value instead of a truthy-looking string — a real
  Pydantic behavior the plan's phase doc didn't anticipate, correctly
  worked around rather than silently producing a flaky test.
- Phase 2's commit explicitly ran `npm run build` and verified the served
  bundle against a live server before closing out, noting this was "the
  step whose omission made the previous feature invisible in the browser"
  (referring to local manual verification during the dynamic-chips plan).
  `static/dist/` is gitignored, so this was a local verification discipline
  note, not a repository state issue — the full rebuild at this commit
  correctly bundles both this feature's and the prior feature's source
  changes together.

Backend test count grew 289 → 297 across these two commits. Every commit's
own `ruff`/`mypy`/test verification was independently re-confirmed at
close-out.

## Dependencies

- None outside this repository. Adds one SQLite column via the existing
  versioned migration system; no new external services or settings.

<!-- slug: bible-favorite-passages -->
