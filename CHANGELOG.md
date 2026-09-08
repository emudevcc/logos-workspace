# Changelog

All notable changes to Logos Workspace are documented in this file.

## 2026-09-07 — Logos Workspace bootstrap

- New public repository `emudevcc/logos-workspace`; baseline tree copied from
  English Cockpit OS at `83090da` and product renamed **Logos Workspace**.
- Roadmap in progress: multi-cockpit app (English · Português · Bíblia).

# Changelog

All notable changes to English Cockpit OS are documented in this file.

## 2026-09-07 — Fresh, beginner-first practice release

### Added

- **Infinite practice content (LLM, with anti-repetition):**
  - Shadowing/dictation sentences are generated on demand at high temperature; the
    card opens on a fresh sentence on every load, `Next` fetches another, and a
    recent-window dedupe stops the same sentence from coming right back.
  - Grammar drills (phrasal verbs, collocations, use-of-English, word forms,
    grammar coach) generate new items each `Next`, also with recent-repeat
    suppression and bounded validation retries.
- **Word & Idiom of the Day generated on the fly** by the LLM on every page load
  and on every content refresh (⟳ / 30-minute cycle). When the LLM is
  unavailable it falls back to the curated pool. The Prev/Next archive
  navigation and date persistence were removed; **＋ Add to review** is kept.
- **Internal content calibration blend** (`app/services/difficulty.py`): roughly
  **80% elementary (A1–A2)** and **20% clear intermediate (B1–B2)** items,
  picked randomly per request — no user-facing levels anywhere.
- **Refresh-cycle wiring:** Word-of-Day, news, and podcast re-roll on the content
  cycle; visible practice prompts (shadowing/dictation, grammar drills, PREP)
  advance automatically only when idle — never clobbering a half-typed answer or
  an on-screen result — and never spend LLM budget on hidden panels.
- **Curated-pool expansion:** irregular verbs 139 (from ~79) and minimal pairs 44
  (from 22). The verb/pair drills cycle their whole pool before repeating
  anything and never reopen on the item shown on the previous page load.
- **Randomization:** SRS due/new queues and podcast episode lists are served in
  random order; PREP scenarios and Word-of-Day random draws avoid immediate
  repeats.

### Changed

- **Removed the whole practice-level system:** the level selector UI, `?level=`
  API parameters, CEFR/numeric schema fields, `/api/levels`, and the
  verb/pair/word-of-day tier labels. Content difficulty is now the internal
  beginner-first blend described above.
- Shadowing & dictation no longer open on a fixed 6-phrase pool (those phrases
  duplicated Word-of-Day vocabulary).
- macOS look: the sidebar "traffic lights" window dots were removed; a spacing
  rhythm and module styling pass was applied as part of the design-token work.

### Fixed

- A stray `null` text node below the sidebar greeting when no streak is active
  (`Element.append(null)` renders a literal `"null"` node).
- Content that always looked the same: Word-of-Day reverting to the same word on
  reload, shadow/dictation reusing the same business phrases, and fixed
  SRS/podcast ordering.

### Quality

- Backend tests: 201 passing; frontend tests: 57 passing; ruff and mypy clean;
  Vite build clean. The server runs behind the `com.englishcockpit.os`
  LaunchAgent and serves `https://localhost:8000/`.

### Design-system artifacts (added to the repo)

- `docs/Project-As-Complete-Opendesign-Design-System.md` and its folder
  (`DESIGN.md`, `tokens.css`, `colors_and_type.css`, `preview/`, `context/`).
- `docs/Web-Prototype/` (`english-cockpit-os.html`, `uiux-plan`, `DESIGN-HANDOFF`).
- `code/tokens.json`.
