# local-code evidence — English Cockpit OS repo

Grounded-notes pulled from the preserved UI/UX pack (`english-cockpit-uiux-plan.md` +
`english-cockpit-implementation.md`) + the design prototype (`english-cockpit-os.html`). This is the
real frontend the design system speculatively refines; no code was fetched into the workspace.

## Repository & stack
- Linked directory: `/Users/esteban/Documents/code_ai/english_cockpit_os`
- Base commit for the UI modernization: `a8b6ade`
- Stack: FastAPI (serves `/`, `/api/*`, `/ws`) · Jinja shell (`templates/index.html`,
  ~180 lines) · Tailwind v4 + DaisyUI v5 theme `cockpit` (`main.css`) · component CSS
  (`cockpit.css`) · vanilla ES modules in `static/js/components/*.js` (15 modules) · Vite →
  `static/dist/` (with zero-build source serving fallback).
- Device: Raspberry Pi 3B kiosk · 1080p TV · Chromium `--disable-gpu` · 1–3 m · no mouse
- Keyspaces: `data-module`, `data-slot` (module content injects into empty slot), DaisyUI `.card`,
  shared `<dialog id="card-modal">`.

## UI structure (index.html)
- Shell: macOS-style `.app-shell` with traffic lights + sidebar ↔ 4-section `main`
  (Today · Practice · Speak · Write). Sections each contain card grids; each DaisyUI `.card`
  (with `data-module`, `aria-labelledby`) opens into a modal.
- Live UI is JS-rendered into `data-slot`; content of each module comes from its component `init()`.

## Modules (14, with data-module keys)
Practice: `srs` (SRS flashcards, new/review badges, grade 1–4) · `prep` (90s timed translate drill) ·
`grammar` (Irregular / Phrasal / Coach, 3-tab) · `shadowing` (Repeat + Playback quiz, 2-tab).
Speak: `voice` roleplay (hold-to-talk) · `speech` metrics coach (Live HUD → Monologue) ·
`radio` live captioned station + teleprompter.
Write: `declutter` Writing Coach (Polish / Correct) · `register` Register Swap (5-tab segmented).
Today: `today` next-step · `word-of-day` · `news` · `podcast` · `weekly-plan`.

## API contract (numbered only from real fields, nothing invented)
- `/api/srs/stats` → `reviews_today`, `daily_review_goal`, `streak`, `total due`, `total new`
- `/healthz` → WS/online status

## Token & accent source of truth
- DaisyUI `cockpit` theme vars (base `#1e1e20`/`#262628`, content `#f5f5f7`) are the single palette
  source in `main.css`; derived aliases live in one scoped `:root` in `cockpit.css`.
- Finalized **C2 module accent map** (14 unique hues) is normative for this repo — see
  `english-cockpit-implementation.md` §C2. Contrast rules: decor-only hues vs bright text variants vs
  deep solid-button fills; yellow-family banned on light fills / <14px text.
- Type stacks: `--font-ui` system sans (chrome) · `--font-serif` Georgia/Iowan (reading) ·
  `--font-mono` ui-monospace (numerics/timer/IPA).

## Cross-cutting repo conventions this package mirrors
- Icon helper `static/js/lib/icons.js` (icon() → inline stroke SVG); emoji-as-icon removal (C3).
- Kiosk read scale + 44px targets + state contrast (C4); a11y: `aria-current`, `aria-selected`,
  modal focus (C5).
- Sidebar status foot via `stats.js` (two-line goal + ring `dashoffset=c·(1−done/goal)`) (C6).
- Card→modal **fresh-render** with `dispose` convention; no live-DOM relocation (C7).
- Reduced-motion + responsive rail collapse at ≤760px (C8).
