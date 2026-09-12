---
title: "Favorite Bíblia studies: a schema v6 flag and a shared-list refactor instead of a fork"
date: 2026-09-11
summary: "Added a persisted is_favorite flag on saved Bíblia studies plus a favorites-only filter and toggle endpoint, then extracted bible_saved_list.js so the new Favoritos view didn't fork ~90 lines of near-duplicate code from bible_history.js."
---

# Favorite Bíblia studies: a schema v6 flag and a shared-list refactor instead of a fork

**Date**: 2026-09-11 17:55
**Severity**: Low
**Component**: Bíblia cockpit — saved studies (`app/core/db.py`, `app/services/bible_studies.py`, `app/api/routes_bible.py`, `static/js/lib/bible_saved_list.js`)
**Status**: Resolved

## What Happened

`plans/260911-2345-bible-favorite-passages/` added a favorite flag to
saved Bíblia studies: a schema v6 migration (`ALTER TABLE studies ADD
COLUMN is_favorite INTEGER NOT NULL DEFAULT 0`), a `favorites_only` query
param on the existing list endpoint, and a new `POST
/api/bible/studies/{id}/favorite` toggle. The flag lives on the saved-study
row, not the passage — favoriting the same passage studied in two
languages produces two independent favorites, each a real reopenable
report, matching how history already treats re-studies as distinct rows.

The frontend side is the more interesting decision: the new Favoritos view
needed the exact same list/open/delete UI as the existing history view,
just filtered differently with a different empty-state string. Rather than
copy `bible_history.js` into a second ~90-line near-duplicate file, Phase 2
extracted the shared logic into `static/js/lib/bible_saved_list.js`
(`initSavedStudyList(slot, {fetchPath, emptyMessage})`), and both
`bible_history.js` and the new `bible_favorites.js` became 13-line
wrappers around it. Shipped across two commits: `3200d19` (backend, 8 new
tests) and `808cf33` (frontend refactor + new view + nav wiring).

## The Brutal Truth

This one went smoothly, which is its own kind of note-worthy after the
LLM-reliability plan's reactive-fix streak earlier the same day — but two
details are worth recording precisely because they're the kind of thing
that silently produces a flaky or misleading test if you don't catch them.

First, Pydantic's lax validation mode will coerce `"yes"` and `"true"`
into `True` for a `bool` field. `FavoriteRequest.favorite: bool` is a
strict `extra="forbid"` body, but "strict extras" doesn't mean "strict
types" — a malformed-body test that sent `{"favorite": "yes"}` expecting a
422 would have silently passed the coerced value through to the route
instead of failing validation, and nobody would have noticed until a
client sent literally that string in production. The fix was using a
non-coercible value for that test case, with a comment explicitly noting
the coercion behavior so a future editor doesn't "fix" the test back into
the trap.

Second — and this is the harder-won lesson — the Phase 2 commit message
explicitly calls out running `npm run build` and verifying the served
bundle against a live server before closing out, describing this as "the
step whose omission made the previous feature invisible in the browser."
That's a direct, named reference to a real gap in the earlier
dynamic-example-passages work: `static/dist/` is gitignored, so a frontend
change can pass every test and lint check, get committed, and still not
exist in what a browser actually loads until someone remembers to rebuild.
That's not a subtle bug — it's a discipline gap that make a shipped
feature functionally absent in production while every CI signal stays
green.

## Technical Details

- Migration: schema v5 → v6, one `ALTER TABLE`, `create_study`'s explicit
  `INSERT` needed no change since the column defaults to 0.
- `list_studies()` gained `favorites_only=False`; the column had to be
  added to both the explicit `SELECT` column list and the field-by-field
  row construction — "the two places that must stay in sync," per the
  commit message, and exactly the mistake the plan's own risk assessment
  had flagged in advance.
- Route shape: `favorites_only` is a query param on the existing `GET
  /api/bible/studies`, not a `/studies/favorites` path segment — chosen
  because `/studies/{study_id}` already uses an int path converter and a
  literal segment there would contend for the same route shape.
- Two mutation checks confirmed the new tests actually bite: dropping
  `is_favorite` from the unfiltered `SELECT` raises `IndexError`; ignoring
  `favorites_only` fails the empty-list assertion.
- Backend test count: 289 → 297 (8 new tests, all in `3200d19`).
- Frontend: `bible_history.js` shrank from carrying its own row-building/
  detail/delete logic to a 13-line wrapper; `wc -l` confirms both
  components are now that size, with the row-building, detail view, and
  delete code existing in exactly one place (`bible_saved_list.js`).

## What We Tried

No failed approaches here — the plan explicitly rejected forking
`bible_history.js` into two near-duplicates as the *first* option
considered, before writing any frontend code, specifically because the two
views only ever differ in fetch path and empty-state copy. That's the
right instinct: recognizing a near-duplicate before it exists is cheaper
than deduplicating it after two files have already drifted.

## Root Cause Analysis

The Pydantic coercion quirk isn't a bug in this codebase — it's
`bool` field lax-mode behavior baked into Pydantic itself, and it would
have bitten any future strict-`bool`-body test written the "obvious" way
(`{"field": "yes"}` expecting rejection). The build-step discipline gap is
the more consequential root cause: the previous plan's frontend changes
were technically complete and tested, but "tested" only covered logic, not
"is this code actually served," and `static/dist/` being gitignored means
that failure mode leaves zero trace in `git status` or CI.

## Lessons Learned

1. Never assume a strict Pydantic model's `bool`/`int`/etc. fields reject
   type-mismatched values the way `extra="forbid"` rejects unknown keys —
   test type coercion with a value that genuinely can't coerce, not one
   that merely looks wrong.
2. For any frontend change in a workspace with a gitignored build output
   directory, "tests pass" and "linted clean" are necessary but not
   sufficient close-out conditions — verify the actual served bundle
   against a live server before marking a plan done. This plan made that
   verification step explicit in its own commit message specifically so
   the next plan doesn't have to relearn it the hard way.
3. When two UI components are about to differ only in a data source and a
   string, extract the shared module before writing the second copy, not
   after. The plan's Scope Challenge section literally states this as the
   reason the frontend refactor doesn't count as scope creep — the
   extraction reduces net new code rather than adding an abstraction
   nobody asked for.

## Next Steps

- No open follow-ups: 297/297 backend tests, `ruff check` clean, `mypy
  app` clean (71 files), 64/64 frontend tests — independently
  re-verified at close-out, matching both commits' own reported gates.
- Carry the "verify the served bundle, not just the tests" discipline
  forward as a standing close-out step for any plan touching
  `static/js/`, given it's now been named twice in one day's worth of
  commits (once as a lesson learned, once as a lesson applied).
