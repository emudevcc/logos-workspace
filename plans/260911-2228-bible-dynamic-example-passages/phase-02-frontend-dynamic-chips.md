---
phase: 2
title: "Frontend Dynamic Chips"
status: pending
priority: P2
effort: "1-1.5h"
dependencies: [1]
---

# Phase 2: Frontend Dynamic Chips

## Goal

Fetch fresh example-passage chips from Phase 1's endpoint on mount and on
every language switch, using the existing hardcoded `I18N[lang].examples`
array as the fallback when the fetch fails or returns nothing — the chip row
must never end up empty or broken.

## Context Links

- `static/js/components/bible_study.js:21-97` — `I18N`: the three
  per-language `examples` arrays this plan keeps as the fallback pool
  (not deleted).
- `static/js/components/bible_study.js:152-160` — `applyChrome()`: currently
  calls `renderChips(strings.examples || [])` synchronously on every chrome
  refresh (init, and each language switch via `renderLangBar`'s handler —
  confirm the exact call site at `bible_study.js:180-`).
- `static/js/components/bible_study.js:162-178` — `renderChips(examples)`:
  clears and rebuilds the chip row from whatever array it's given; this
  function's contract doesn't need to change, only what's passed to it.
- `static/js/components/word_of_day.js:17-25` — the `load()` /
  `apiGet(...).catch` pattern to mirror for the new fetch, adapted to
  "fall back to a local array" instead of "render an error state" (this
  card should never show a visible error for a missing chip suggestion —
  worst case is the existing static chips, exactly like today).
- `static/js/lib/api.js` — `apiGet(path)` already used throughout the
  frontend; `GET /api/bible/example-passages?language=<lang>` follows the
  same call shape.

## Key Insights

- `applyChrome()` runs synchronously today; fetching chips is async, so the
  chip row must render the fallback array immediately (no flash of empty
  chips while the request is in flight) and swap in the fetched list only
  if/when it arrives and is non-empty. This matches how `word_of_day.js`
  starts blank and fills in once `load()` resolves, except here the
  "blank" state has a perfectly good non-blank default already.
- Fetching on every language switch means up to 3 fetches per session in
  normal use (one per language the user tries) — not a refresh cycle, not
  tied to the ⟳/30-min content cycle other cards use, since there's no
  README-documented recurring refresh for this card and one wasn't asked
  for. Mount + language switch is the full trigger set.
- No component-mount test harness exists for any cockpit component
  (established in the prior plan's Phase 4 — `tests/frontend/` covers
  `static/js/lib/*` units only). This phase follows the same precedent: no
  new test infrastructure for `bible_study.js`'s closures; verify by grep +
  a manual check instead of building one now.

## Requirements

- [x] Add an `async function loadChips()` that calls
      `apiGet(\`/api/bible/example-passages?language=${language}\`)`,
      and on success with a non-empty array, calls `renderChips(result)`;
      on any error (network failure, non-200 — `apiGet` throws `ApiError`
      the same way it does elsewhere) or an empty array, leaves whatever
      `renderChips` already rendered (the curated fallback) untouched — do
      not clear the chip row while waiting or on failure.
- [x] `applyChrome()` still calls `renderChips(strings.examples || [])`
      synchronously first (the immediate, correct-for-the-language
      fallback), then `applyChrome()`'s caller kicks off `loadChips()`
      without awaiting it (fire-and-forget; the UI must not block on this
      network call).
- [x] `loadChips()` runs once on `init(slot)` (initial mount) and once per
      language change (wherever `applyChrome()` is already invoked on
      switch — reuse that call site, don't add a second one).
- [x] Guard against a stale response clobbering a newer one: if the user
      switches languages quickly, a slow `es` response arriving after the
      user has already switched to `en` must not overwrite the `en` chips.
      Track the language the in-flight request was made for and discard
      the result if `language` has since changed (a simple closured
      "request token" or comparing the captured language against the
      current one at resolution time both work — pick the simpler one).
- [x] Document the new endpoint in `docs/API.md`, matching the existing
      Bíblia section's row style (method, path, notes).

## Architecture

```
bible_study.js
  function applyChrome() {
    ...
    renderChips(strings.examples || []);  // immediate fallback, unchanged
    loadChips();                          // fire-and-forget refresh
  }

  async function loadChips() {
    const requestedLang = language;
    try {
      const fresh = await apiGet(`/api/bible/example-passages?language=${requestedLang}`);
      if (requestedLang !== language) return;  // stale — language changed mid-flight
      if (Array.isArray(fresh) && fresh.length) renderChips(fresh);
    } catch {
      // keep the fallback already on screen; no error state for this card
    }
  }
```

## Related Code Files

- Modify: `static/js/components/bible_study.js`
- Modify: `docs/API.md`

## Implementation Steps

1. Read `static/js/components/bible_study.js`'s full `applyChrome`/
   `renderChips`/language-switch call chain (lines ~152-230) before editing,
   to find every call site of `applyChrome()` that needs the new
   `loadChips()` call alongside it.
2. Add `loadChips()` per the Architecture block, using the existing
   `apiGet` import already at the top of the file.
3. Call `loadChips()` from every place `applyChrome()` runs (mount and
   language switch) — do not duplicate the fallback-render logic, only add
   the fetch-and-maybe-replace step.
4. Add the new endpoint's row to `docs/API.md`'s Bíblia section, matching
   the existing table's columns and style.
5. Run `npm test` (no new test added per Key Insights — this step is the
   regression smoke-check).
6. Manually verify in a browser: load the Bíblia cockpit, confirm chips
   appear immediately (fallback) and then may refresh to a different set
   shortly after (LLM configured) or stay the same (LLM not configured —
   confirm no console error, no flash of empty chips); switch language
   rapidly a few times and confirm no chip-set from the wrong language
   ever appears.

## Todo List

- [x] `loadChips()` added, fire-and-forget, never clears chips on failure
- [x] Stale-response guard (language changed mid-flight)
- [x] Wired into mount and every language-switch call site
- [x] `docs/API.md` documents the new endpoint
- [x] `npm test` passes
- [x] Manual browser check: immediate fallback, no empty-chip flash, no stale-language chips on rapid switching

## Success Criteria

- With the backend endpoint unreachable (e.g. stop the server mid-session
  in a manual check, or temporarily 404 it), the chip row still shows the
  correct-language curated examples — never empty, never a visible error.
- Rapidly switching es → en → pt never leaves a chip row showing another
  language's passages once all in-flight requests have settled.
- `npm test` (64 existing tests, unless Phase 1 or 2 added any) still passes.

## Risk Assessment

- **Risk:** Forgetting to guard against stale responses could show, e.g.,
  Portuguese passage suggestions while the UI has already switched to
  English — confusing and hard to notice in casual testing (it only shows
  up under fast switching). **Mitigation:** the stale-response guard is a
  Requirement, not an afterthought, and the manual check explicitly
  exercises rapid switching.
- **Risk:** If `loadChips()`'s fetch is slow and the user clicks a fallback
  chip before it resolves, then the fetch completes and silently replaces
  the chip row — mildly surprising but not harmful (the click already fired
  `run()` with the chip's text, independent of what the chip row shows
  afterward). **Mitigation:** none needed; this is normal, low-stakes
  behavior consistent with how a chip's `onclick` closes over its own
  `example` string at render time, not a live reference to the array.

## Security Considerations

- No new user input surface on the frontend; `language` is already a
  closed, internally-set value (`readLang()`/the language selector), not
  free text from the user.

## Next Steps

- None — this is the last phase. After both phases: re-run `ruff check`,
  `mypy app`, the backend suite, and `npm test` once more as a final gate,
  and update `CHANGELOG.md` with an entry for this feature (matching the
  existing changelog's style, as every feature in this streak has).
