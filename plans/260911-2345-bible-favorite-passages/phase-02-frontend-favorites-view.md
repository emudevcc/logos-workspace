---
phase: 2
title: "Frontend Favorites View"
status: pending
priority: P1
effort: "1.5-2h"
dependencies: [1]
---

# Phase 2: Frontend Favorites View

## Goal

Extract `bible_history.js`'s list/open/delete logic into one shared module,
add a star toggle to it, and build a new `bible_favorites.js` — a thin
wrapper over the same module, fetching the favorites-only filter — with its
own nav tab, mirroring `bible-history`'s registration exactly.

## Context Links

- `static/js/components/bible_history.js` (full file, 117 lines) — every
  piece of this file except its Spanish empty-state string and its fetch
  path (`/api/bible/studies`) is identical to what the new favorites view
  needs: `loadList()`, `buildRow()`, `loadPrefs()`, `openStudy()`,
  `showList()`, the local `apiDelete()` helper (there's no `apiDelete` in
  `static/js/lib/api.js` — only `apiGet`/`apiPost` — so this file rolled its
  own; the extracted module keeps that one copy instead of a second).
- `templates/index.html:49-52` — the `bible-history` nav button (exact
  markup to mirror, same icon-svg-then-label shape).
- `templates/index.html:247-257` — the `bible-history` `app-view` section
  (`data-view-panel="bible-history"`, a `card` with `data-module=
  "bible-history"` and a `data-slot` div `main.js` mounts into).
- `static/js/main.js:16,61,203` — `bible-history`'s three registration
  points: the module import, the view→module map entry, and the icon-svg
  map entry. A fourth `bible-favorites` view needs the same three additions.
- Phase 1's `POST /studies/{id}/favorite` (body `{"favorite": bool}`,
  `FavoriteRequest` has `extra="forbid"`) and `GET /studies?favorites_only=
  true` — the two endpoints this phase wires up.

## Key Insights

- `bible_history.js` and the new favorites view differ in exactly two
  things: the fetch path/query and the empty-state message. Forking the
  file would duplicate ~90 lines (list loading, row construction with two
  action buttons, prefs loading, detail-view open/back navigation, the
  local delete helper) for a one-line difference each. Extracting a shared
  factory is the direct DRY move here, not an abstraction invented ahead of
  need — there are exactly two call sites today, both real.
- The extracted module owns the star-toggle logic once, so both views
  render and behave identically for a study's favorite state — no risk of
  the star button working slightly differently in one view vs. the other.
- `FavoriteRequest`'s `extra="forbid"` (Phase 1) means the toggle call must
  send **exactly** `{"favorite": <bool>}` — not the whole `summary` object.
- No new component-mount test infrastructure is added here, consistent with
  the precedent already set twice in this workspace (the LLM-reliability
  plan's Phase 4, and the dynamic-example-passages plan's Phase 2): no
  existing test file mounts a full cockpit component, and building that
  harness now — for what is otherwise a small, directly-verifiable UI
  change — would be disproportionate. Verified by `npm test` (regression)
  plus a manual browser check.

## Requirements

- [x] New `static/js/lib/bible_saved_list.js` exporting
      `initSavedStudyList(slot, { fetchPath, emptyMessage })`, containing
      everything `bible_history.js` currently does (`loadList`, `buildRow`,
      `loadPrefs`, `openStudy`, `showList`, the local `apiDelete` helper),
      parameterized by `fetchPath` (e.g. `"/api/bible/studies"` or
      `"/api/bible/studies?favorites_only=true"`) instead of the hardcoded
      URL, and by `emptyMessage` instead of the hardcoded
      `"Todavía no hay estudios guardados."` string.
- [x] `buildRow()` in the shared module gains a star button before "Abrir":
      label `"★"` when `summary.is_favorite` is true, `"☆"` otherwise
      (or an equivalent visually-distinct pair — match the existing chip
      button styling, no new CSS class needed beyond the existing `chip`
      class already used for "Abrir"/"Borrar"); `onclick` calls
      `apiPost(\`/api/bible/studies/${summary.id}/favorite\`, { favorite:
      !summary.is_favorite })` then `loadList()` to refresh (matching the
      delete button's existing "mutate then reload" pattern — no optimistic
      local state).
- [x] Rewrite `static/js/components/bible_history.js` to a thin call:
      `export function init(slot) { initSavedStudyList(slot, { fetchPath:
      "/api/bible/studies", emptyMessage: "Todavía no hay estudios
      guardados." }); }`.
- [x] New `static/js/components/bible_favorites.js`:
      `export function init(slot) { initSavedStudyList(slot, { fetchPath:
      "/api/bible/studies?favorites_only=true", emptyMessage: "Todavía no
      tienes estudios favoritos." }); }`.
- [x] Register `bible-favorites` in `static/js/main.js`: import the new
      component, add it to the view→module map next to `"bible-history":
      bibleHistory,`, and add an icon-svg entry next to `"bible-history"`'s
      — use a star-shaped path (e.g. lucide's star:
      `<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>`),
      not a reused icon, so the tab is visually distinct from Historia.
- [x] Add the nav button and `app-view` section to `templates/index.html`,
      copying `bible-history`'s exact structure
      (`data-view="bible-favorites"`/`data-view-panel="bible-favorites"`,
      `data-cockpit="bible"`, `data-module="bible-favorites"`), placed
      directly after the existing Historia entries so the Bíblia nav order
      is Estudio → Historia → Favoritos → Libros. Label the button
      "Favoritos" and the view title "Favoritos".
- [x] Add the new/changed endpoints to `docs/API.md`'s Bíblia section:
      `GET /api/bible/studies?favorites_only=` (note on the existing
      `/studies` row) and `POST /api/bible/studies/{id}/favorite`.

## Architecture

```
static/js/lib/bible_saved_list.js
  export function initSavedStudyList(slot, { fetchPath, emptyMessage }) {
    // body = bible_history.js's current init(), parameterized:
    // - loadList() fetches `fetchPath` instead of a hardcoded "/api/bible/studies"
    // - the empty-state <p> uses `emptyMessage` instead of the hardcoded string
    // - buildRow() gains the star button described above
    // - apiDelete, loadPrefs, openStudy, showList move here unchanged
  }

static/js/components/bible_history.js
  import { initSavedStudyList } from "../lib/bible_saved_list.js";
  export function init(slot) {
    initSavedStudyList(slot, {
      fetchPath: "/api/bible/studies",
      emptyMessage: "Todavía no hay estudios guardados.",
    });
  }

static/js/components/bible_favorites.js
  import { initSavedStudyList } from "../lib/bible_saved_list.js";
  export function init(slot) {
    initSavedStudyList(slot, {
      fetchPath: "/api/bible/studies?favorites_only=true",
      emptyMessage: "Todavía no tienes estudios favoritos.",
    });
  }

main.js
  import * as bibleFavorites from "./components/bible_favorites.js";
  // view map: "bible-favorites": bibleFavorites,
  // icon map: "bible-favorites": '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
```

## Related Code Files

- Create: `static/js/lib/bible_saved_list.js`
- Modify: `static/js/components/bible_history.js`
- Create: `static/js/components/bible_favorites.js`
- Modify: `static/js/main.js`
- Modify: `templates/index.html`
- Modify: `docs/API.md`

## Implementation Steps

1. Read `static/js/components/bible_history.js` in full (already scouted;
   re-read immediately before editing to catch anything since scouting).
2. Create `static/js/lib/bible_saved_list.js`, moving that file's logic in
   per the Architecture block, parameterizing `fetchPath`/`emptyMessage`,
   and adding the star button to `buildRow()`.
3. Rewrite `bible_history.js` to the thin wrapper shown above.
4. Create `bible_favorites.js` as the second thin wrapper.
5. Register the new view in `main.js`: import, view-map entry, icon-map
   entry (three separate edits, per Context Links' line numbers).
6. Add the nav button and section to `templates/index.html`, copying
   `bible-history`'s block and adjusting `data-view`/`data-view-panel`/
   `data-module`/label/title to `bible-favorites`/"Favoritos".
7. Update `docs/API.md`.
8. Run `npm test` (regression check — no new test file per Key Insights).
9. Manual browser check: open Bíblia → Historial, confirm existing rows
   still list correctly and the new star button appears and toggles (check
   it persists across a reload); open the new Favoritos tab, confirm it's
   empty until something is starred, confirm starring/unstarring a study
   from either tab is reflected correctly in both after switching tabs
   (reload triggers a fresh fetch each time you switch into a view, so no
   stale-state concern here — confirm that's still true after the refactor).

## Todo List

- [x] `bible_saved_list.js` created, parameterized, includes the star button
- [x] `bible_history.js` reduced to a thin wrapper (behavior unchanged plus the star button)
- [x] `bible_favorites.js` created as the favorites-only wrapper
- [x] `main.js` registers the new view (import + view map + icon map)
- [x] `templates/index.html` has the new nav button + section
- [x] `docs/API.md` documents the new/changed endpoints
- [x] `npm test` passes
- [x] Manual check: star toggle persists, Favoritos tab reflects it, empty state shows correctly

## Success Criteria

- `bible_history.js` and `bible_favorites.js` are both thin (a handful of
  lines each); the shared logic lives in exactly one place
  (`bible_saved_list.js`).
- Starring a study from the Historial tab and switching to Favoritos shows
  it there; unstarring it from either tab removes it from Favoritos on next
  load.
- The Favoritos tab's empty state reads "Todavía no tienes estudios
  favoritos." (distinct from Historial's message), confirming the
  parameterization actually varies per call site rather than being
  hardcoded once and reused verbatim.
- `npm test` (64 tests as of the last plan, plus any Phase 1 additions —
  Phase 1 is backend-only, so the frontend count is unaffected) passes
  unchanged.

## Risk Assessment

- **Risk:** Sending `{ favorite: !summary.is_favorite, id: summary.id }` or
  similar to the toggle endpoint would 422 against Phase 1's
  `extra="forbid"` `FavoriteRequest`. **Mitigation:** the Requirements
  bullet above states the exact body shape (`{ favorite: bool }` only);
  follow it literally.
- **Risk:** Refactoring `bible_history.js` into a thin wrapper could
  silently change behavior if any closure state (e.g. `prefs`) was assumed
  to be module-level rather than per-call. **Mitigation:** every piece of
  state in the current file (`prefs`, the list/detail elements) is already
  local to `init()`'s closure, not module-level — moving the whole closure
  body into a parameterized function preserves that scoping exactly; the
  manual check's "switch tabs, confirm no stale state" step is the
  regression signal if this assumption is wrong.

## Security Considerations

- No new user input; `study_id` in the toggle URL is the same integer
  already used for open/delete in the existing history rows.

## Next Steps

- None — this is the last phase. After both phases: re-run `ruff check`,
  `mypy app`, the backend suite, and `npm test` once more as a final gate,
  and add a `CHANGELOG.md` entry for this feature, matching the existing
  changelog's style.
