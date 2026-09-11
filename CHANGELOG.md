# Changelog

All notable changes to Logos Workspace are documented in this file.

## 2026-09-11 — Dynamic Bíblia example-passage chips

- The Bíblia study input's example chips are now **LLM-generated on each load**
  instead of a fixed list of six per language. New
  `GET /api/bible/example-passages?language=es|en|pt` returns a fresh, varied
  set (mixed OT/NT, no repeated book), and a per-language recent-window keeps
  consecutive loads from serving the same references.
- **Every suggestion is validated before it is shown.** Each candidate
  round-trips through the real reference parser, and anything unparseable — a
  hallucinated book, a malformed reference — is dropped rather than served,
  so a bad suggestion can't 422 or feed a wrong passage into study generation.
- **The chip row can never break.** The endpoint returns `200` with `[]` for
  any LLM problem (not configured, budget exhausted, upstream error, malformed
  JSON), and the frontend renders the curated examples immediately, replacing
  them only if a non-empty list arrives — so no empty-chip flash and no visible
  error, even with the backend unreachable.
- The refresh is fire-and-forget and guarded against stale responses, so
  switching language rapidly never leaves another language's chips on screen.
- The endpoint is deliberately not rate-limited, matching
  `/api/word-of-day/random`: a suggestion fetched per mount/language-switch
  must not consume the shared 30/min budget a real study submission needs.

## 2026-09-11 — Bíblia LLM reliability hardening

### Fixed

- **Unbounded log growth on the macOS LaunchAgent.** `data/logos-agent.log` was
  never rotated and shares a volume with `data/cockpit.db`. The app now
  attaches a size-capped `RotatingFileHandler` to its own `data/logos.log`
  (`LOG_MAX_BYTES`, default 5 MB; `LOG_BACKUP_COUNT`, default 3), installed by
  the `python -m app` entrypoint so it covers both deployment targets with no
  root. Rotation targets a separate file from the LaunchAgent redirect on
  purpose: the running process holds that file open, so renaming its inode
  would leave the renamed archive still growing while the new file stayed
  empty. `LOG_MAX_BYTES=0` restores the old stream-only behaviour.
- **429 handling slept twice per retried attempt.** The `Retry-After` wait and
  the jittered backoff both fired for the same retried network attempt. Only one
  applies now: a 429 whose `Retry-After` was honored skips the backoff; 5xx and
  header-less 429s still back off normally. `docs/DEPLOYMENT.md` documents the
  corrected worst-case latency for a study (no new setting).
- **`LLMBudgetExceeded` on `/api/bible/study` returned 502** instead of reaching
  the app's own 429 handler, because the route intercepted the base `LLMError`.
- **The global `LLMError` handler returned unbounded upstream/model text**; it is
  now capped at 200 characters, and `_extract_content` no longer embeds the full
  response dict.
- **Rate-limit detection in the frontend matched `429` inside the error message
  text** — any wording change could hide the retry affordance. It now uses
  `error.status`.

### Added

- **Typed LLM error taxonomy.** `LLMJsonValidationError` replaces the
  substring-matching of `json_validate_failed` / `"Failed to generate JSON"`
  that was duplicated across `bible_studies.py`, `routes_bible.py`, and
  `bible_study.js`. Detection is structural (Groq's `error.code`) with a
  logged substring fallback for other providers.
- **Schema-shape mismatch retry.** A response that is valid JSON but the wrong
  shape previously got zero retries. It now retries once with a hint naming the
  actual failing field paths (from Pydantic's `loc`/`msg` — never the model's
  own input values), distinct from the JSON-syntax hint.
- **Retry/exhaustion logging.** `app/services/llm.py` gained a module logger and
  `bible_studies.py`'s previously-unused logger is now wired up, so every
  retried attempt, fallback detection, and exhausted failure is visible in the
  deployed log. `docs/DEPLOYMENT.md` documents both log locations (macOS
  LaunchAgent vs. Pi/systemd) and every line the Bíblia path emits.

### Tests

- 16 new backend tests (244 → 260): the corrected single-sleep 429 path plus its
  backoff fallbacks (no header, unparsable header, above the 15 s honor cap), a
  direct `_retry_after_seconds` suite covering delta-seconds and HTTP-date forms
  and the unusable-input paths, the typed exceptions for both 400 and 200 body
  shapes, the schema-mismatch retry (asserting the hint's field-path content),
  the friendly detail with no `input_value` leak, and `LLMBudgetExceeded` → 429
  routing.

### Known gap

- `data/logos-agent.log` itself (the LaunchAgent's stdout/stderr redirect) still
  is not rotated — macOS `newsyslog` needs root and cannot copy-truncate, so it
  would rename the inode out from under the running process. The app's own
  records now go to the rotating `data/logos.log` instead, so the unrotated file
  only grows with uvicorn's startup lines and any third-party output; truncate
  it in place (`: > data/logos-agent.log`) if it ever matters.

## 2026-09-08 — Bíblia em três idiomas (ES · EN · PT)

- Bíblia cockpit passage text is now selectable between **Español / English /
  Português** (defaults **NTV · NIV · NVT**, your API.Bible versions). Study
  output stays in Spanish.
- API.Bible discovery is multilingual (spa/eng/por catalogs); labels are
  configurable via `BIBLE_DEFAULT_TRANSLATION`, `BIBLE_ENGLISH_TRANSLATION`,
  `BIBLE_PORTUGUESE_TRANSLATION`.
- New endpoints: `GET /api/bible/prefs` (selector defaults) and
  `GET /api/bible/translations` (discovered versions).
- Flag language selector (🇪🇸 · 🇺🇸 · 🇧🇷) drives the whole study experience:
  instructions and the six-section report follow the chosen language
  (Spanish default); switching re-generates the current study.

## 2026-09-08 — Logos Workspace 1.0 (M1–M4)

### Added

- **Cockpit framework (M1):** one shell, three cockpits (English · Português ·
  Bíblia). Segmented cockpit switcher, per-cockpit nav/views with remembered
  last view, lazy per-cockpit module mounting (hidden cockpits never spend LLM
  budget), cockpit-scoped SRS (`?cockpit=`), schema migration v2
  (`decks.cockpit`), Bible API config settings, app renamed **Logos Workspace**.
- **Português cockpit (M2):** Palavra do dia, Notícias do Brasil (G1/Exame/
  Tecnoblog), PT-BR SRS decks (Vocabulário essencial · Falsos cognatos ES→PT,
  36 cards) with `l1_hint` Spanish scaffolding (migration v3), grammar rules +
  LLM coach targeting Spanish-transfer traps, minimal pairs and pronunciation
  pitfalls, practice sentences with `pt-BR` audio.
- **Bíblia cockpit (M3):** 66-book registry, PT/ES/EN pericope reference parser,
  API.Bible text provider with SQLite passage cache (migration v4), six-section
  exegesis reports (literary · historical-grammatical · lexical with consensus
  notes · redemptive-theological · principle · application) generated under the
  agreed guardrails, saved studies + history endpoints.
- **Docs & operations (M4):** README/docs rewritten for the multi-cockpit
  product, changelog, macOS LaunchAgent for Logos Workspace
  (`deploy/macos/install-logos-agent.sh`, port 8090, legacy English agent on
  8000 untouched).

### Notes

- Default Bible translation is **RVR09** (public domain) because API.Bible's
  Spanish catalog does not offer RVR60; `BIBLE_DEFAULT_TRANSLATION` selects an
  alternative when another source is added.

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
