# English Cockpit OS — UI/UX Plan

**Intent** — One cohesive UI/UX refinement pass over the whole English Cockpit OS frontend (shell, information architecture, stats, and every interaction-heavy module), keeping the **macOS-native dark skin + Kindle-style serif reading stack** and the existing sidebar ↔ 4-section ↔ DaisyUI-card ↔ modal structure. The goal is a calmer, more consistent, glanceable-at-1–3 m dashboard that looks shipped rather than assembled, without new render-bound cost (Raspberry Pi 3B kiosk, 1 GB RAM, `--disable-gpu`).

**Scope decided with the manager**
- World: **whole app** — shell + all modules.
- Direction: **refine the current system** (no palette/type rebuild).
- Environment: **1080p TV/monitor at ~1–3 m** viewing distance, Chromium kiosk.

---

## Current state (grounded audit)

- Frontend: vanilla ES modules; **Tailwind v4 + DaisyUI v5** (`main.css` theme `cockpit`), Vite-bundled to `static/dist/`. Runs zero-build from source when no bundle. FastAPI serves `/`, `/api/*`, `/ws`.
- Shell: macOS-style sidebar (`Today · Practice · Speak · Write`) → 4 card grids → each card opens into a **DaisyUI modal**.
- Latest commit already added the sidebar skin, DaisyUI cards, accent top-borders, and MagicUI-style effects (spotlight, shimmer, animated gradient border, fade-in).

### Known issues surfacing in the audit (candidate backlog — prioritize in Design mode)

**A. Two parallel style systems / dead code (high value, low risk)**
- `cockpit.css` still holds the legacy `:root` hex tokens + `.cockpit-header`, `.cockpit-grid`, `.cockpit-card`, per-module accent-bar map, `.hud*`, etc. `main.css` re-introduces macOS shell rules that duplicate parts of `cockpit.css` (e.g. `.app-shell`, `.traffic-lights` exist in **both** files). DaisyUI `card` accents are duplicated with a **second** copy both in `cockpit.css` and `main.css`.
  - → Consolidate tokens into **one** home (the DaisyUI `cockpit` theme vars + a single `:root` alias block in `main.css`), delete the legacy `.cockpit-*`/header rules and duplicate accent maps. Document that `cockpit.css` keeps only component-internal rules (transcript, chips, drills, HUD…).

**B. Visual inconsistency**
- Mixed accents for the same semantic thing: `#0a84ff` is the primary nav/accent but also several module cards, the spotlight glow, and the sidebar's "Today" card — one hue carries most of the identity load; **6 modules share `#ff9f0a` or `#bf5af2` accent tops**, several share `#0a84ff`/`#ff9f0a` as distinct modules, and one tab uses `#ffd60a` (low-contrast) for shadowing. Cards rely almost entirely on a **1 px colored top border** for identity.
  - → Give each module one unique, contrast-safe accent (a fixed 14-slot mapping), then on hover/focus shift by OKLch `L`, never toward a lighter text. Ensure accent never appears more than twice per screen.

**C. Icon language split**
- Nav uses **SVG stroke icons**, but module chrome still leans on **emoji & text glyphs as functional controls**: `🔊` (pronounce everywhere), `🔥` (streak), `🎤`, `✅`, `💡`, and the bare `→` plus the plain-character `↗` (open-modal cue) and `✕` (close) do the job inline where the SVG system should. Mixed iconography across components.
  - → Replace every functional icon with a consistent, small **stroke-SVG icon helper** (play/pause/pronounce/refresh/export/mic/check/close/streak/arrow) reused across components in the existing 16 px stroke style.

**D. Status / stats treatment**
- Nav has an `offline` text pill; `stats.js` renders greeting + 🔥 streak + goal ring + countdown + refresh into the sidebar. Mixed Chrome, emoji, and text; crowding at 15rem sidebar width.
  - → Treat the sidebar foot as a compact, tappable dashboard panel: real-icons, tabular-nums, one clear live/habit status cue; move countdown behind the refresh icon tooltip. Design for min 44 px targets, `tabular-nums`, high-contrast state pairs.

**E. Glanceability at 1–3 m**
- All card text is small (~0.85–0.95rem) even though there is abundant 1080p space; Today's overview is a uniform grid of equal-weight cards (info hierarchy weak: "next step", word-of-day, news, podcast, weekly plan all look alike).
  - → Rebalance Today's hierarchy (lead the actionable "next step" + progress first, demote news/podcast), raise a `--reading-scale`/index for the kiosk, but keep flexibility for near use.

**F. Interaction & correctness nits**
- Spotlight glow, shimmer sweep, and animated gradient border are all **pointer/GPU-driven** effects a kiosk user (no mouse, `--disable-gpu`) rarely sees or pays for; and the rotating gradient border runs a 6s CSS animation continuously.
  - → Gate heavy effects behind fine-pointer + reduced-motion + capability, or drop non-value ones; keep the fade-in.
- Modal currently **moves the live DOM node** out of its card into the modal body then moves it back; two modules instantiated in-place can render into a modal-sized context differently. Docs/FRONTEND still describe the **old** "focus mode" (full-screen `is-focus`) that no longer exists.
  - → Choose one detail pattern and make it first-class (see Card-modal in the screen table and open question 1); update docs/FRONTEND.md to the actual interaction model.
- Global click-to-translate dictionary runs on **every document click**; card buttons/links/inputs/titles are excluded, but toolbars and pre-created affordances are not clearly excluded — verify no interactive chrome words get swallowed mid-click.
- Today/word-of-day/news rows grow while the fixed `app-main` scrolls only inside main; on a 1080p panel the layout must guarantee no horizontal scroll and full fit; several accents (yellow) may fail 3:1 contrast for small live text — check each.

**G. Docs drift**
- `docs/FRONTEND.md` “Design language”, “Focus mode”, component interaction table, and file layout are stale w.r.t. the sidebar/modals/effects added in the last commit. Update to the real interaction contract as part of the pass.

---

## Direction (kept)

- **Palette**: reusable DaisyUI `cockpit` theme vars (base `#1e1e20` / `#262628` / content `#f5f5f7`), one canonical `:root` alias block. Accents = Apple system colors made unique per module; all derived via OKLch when variants are needed. No new global hue.
- **Type**: system sans for chrome/UI + Georgia/Iowan serif for reading surfaces (definitions, briefs, captions, shadowing sentences). Mono (`ui-monospace`) for numerics, timer, IPA. Add a modest kiosk reading scale.
- **Language**: quiet, precise English UI copy (existing tone). Remove emoji-as-icon; SVG stroke icons; one keyboard-first focus ring (`--focus`) everywhere; 44 px touch/hover targets.

## Screen & flow plan

The app is a **single page with 4 sections** (panels) whose cards each contain a full module; modules keep their existing working interactions. Deliverable = shared CSS/JS + small module-chrome edits, not new screens.

| ID | Screen / region | Goals & key changes | Interaction + state notes |
|---|---|---|---|
| S01 | **Shell / sidebar** | Collapsed-into-launcher chrome without losing info: brand, 4 nav items, one foot status panel. Nav = large obvious targets with SVG mark + title. | `is-active` uses accent-on-surface with white text swap (not opacity-only); visible focus ring per state; active view persists via `localStorage`. |
| S02 | **Nav status foot** | Greeting + streak, daily-goal ring, content-refresh countdown as one compact panel; real SVG icons; tabular-nums; readable at 1–3 m. | Ring animates only on state change (not a perpetual sweep); refresh countdown lives behind the ⟳-style icon’s label in the same panel; WS pill surfaces top-of-main when offline. |
| S03 | **Today overview** | Reordered hierarchy: primary “Today/next-step + goal” block, then word/idiom, then news/podcast/weekly-plan in lighter-weighted row. Uniform card shell, varied emphasis. | Card ≡ single tap → modal. Secondary text links inside cards do not navigate away. |
| S04 | **Practice cards** | SRS deck (+ new/review badges), PREP drill (countdown), Verbs & Grammar (7-tab), Pronunciation (3-tab). Per-module accent used only on the icon chip + the active surface (max two appearances per screen). | Space/1–4 to grade; 90 s countdown in large tabular numerals; every save-to-SRS affordance labeled explicitly. |
| S05 | **Speak cards** | Voice roleplay (hold-to-talk), Speech-Metrics coach (Live HUD + Monologue), Live Radio & teleprompter. | Hold/tap states need clear pressed/armed affordance at 44 px; transcript history capped 50 lines; radio pause/clear obvious. |
| S06 | **Write cards** | Writing Coach (Polish/Correct) and Register Swap (5-tab register). | Two distinct calls with one primary style per card, second secondary; register segmented tab control macOS style. |
| S07 | **Card-modal (shared)** | One deterministic detail pattern replacing live-DOM move; consistent header, close, sticky footer actions, scrollable body. | Modal = DaisyUI `<dialog>`; body content **rendered fresh** for the target module on open (no node relocation) so layout is consistent in the roomier modal; Esc + backdrop dismiss; Esc closes don't re-trigger launcher states. |
| X-mod | **Cross-cutting module chrome** (through all above) | Buttons/chip/segmented/audio/chips/dictionary popover/hints all re-skinned to the one variable/theme set; emoji → SVG via a small icon helper. | Keyboard focus + `:hover`/`:active` contrast pairs checked per control; global translate click-ignore extended to toolbar/affordance chrome. |

*Screen-equivalents:* The app is single-page; treat each module surface as a screen-equivalent for review (per project-depth: real product UI with working interactions). No separate screen files — the pass edits `templates/index.html` + `static/css/*.css` + module `static/js/components/*.js` in place.

---

## Design system & token work

1. **Single source of tokens** — leave DaisyUI `cockpit` theme in `main.css` as the platform layer; define derived aliases once (surfaces, borders, text+muted, focus ring, kiosk scale) in one scoped `:root` block so `cockpit.css` and the DaisyUI classes stay consistent.
2. **Module accent map (14)** — assign each `data-module` a stable, unique, contrast-safe accent (OKLch-checked at live-text sizes). Tag accent use: icon chip + active tab per screen is the peak; never more than two fields of the same hue at once.
3. **State contract** — hover/focus move background by ±0.06–0.12 OKLch L or adjust border/shadow; foreground **never** lightens; single visible `:focus-visible`; disabled is the only contrast-reducing state. Focus ring in every module.
4. **Scale** — raise base + card-title + nav + status to a 1080p-friendly index (goal ~ 16–18 px UI, 20–24 px titles), keeping readable text wrapping and no horizontal scroll; still fine at arm's length. Provide `meta color-scheme dark` (already set).

## Data / content model (no fabricated data)

- Keep every current API call and schema exactly as-is. Only presentation changes: countdown/refresh/streak renders derive from the **same** API fields (`/api/srs/stats` → reviews_today, daily_review_goal, streak, total due/new; `/healthz` → ws status). No new endpoints, no invented metrics — replace only how the values are shown (SVG ring, tabular numerals, spacing). Visible “next step” copy may only surface real due/new/goal numbers.
- Where a loading/empty/error state exists on-device, keep the real API response text; do not invent placeholder copy beyond honest screen states.

## Verification & acceptance

Walk (ideally on the running app / kiosk) the three keystone flows and the shared modal:

1. **Navigation + states** — the sidebar nav switches panels, preserves state across reload, has a visible focus ring on keyboard nav, and its active state never loses accent readability.
2. **Study flow** — Today → open SRS modal → grade cards 1–4 → the due/goal/streak numbers in the sidebar update; PREP countdown ticking large; grammar drill saves to SRS with clear confirmation.
3. **Speak + Write flows** — Voice roleplay visible armed/recording state at 44 px; radio live-caption + clear/pause obvious; Writing Coach’s Polish vs Correct distinction clear (one primary per card).
4. **Shared modal + translate** — every card opens/edits/closes predictably with node-count parity (no duplicate event-bus storms, no leftover listeners), Esc dismisses cleanly, and global click-to-translate never triggers on privileged chrome.

Automated gates (already present, must remain green): `npm test` (55) and `.venv/bin/python -m pytest -q` (~175). Build must pass `npm run build` and the unbundled dev serving still parses.

Additional self-review for the whole page at 1080p: no horizontal scroll, no clipped/overlapping elements, each accent at used text size ≥ 4.5:1 (body small) / ≥ 3:1 (large + icons), one decisive flourish only (keep fade-in; gate spotlight/shimmer/rotating border behind fine-pointer so kiosk users aren't charged).

## Open questions for the manager (design uses the defaults unless told otherwise)

1. **Card-modal fine art (S07)** — do we keep a dedicated full role (“open in modal”) for every card, or drop modal and make deeper modules their own container panels that tile on Today? Default: keep single shared modal, fresh-render body, Esc/backdrop close; kills the live-DOM-move fragility.
2. **Today emphasis (S03)** — keep news/podcast digest feeds as low-weight list-strips (denser, more air), or keep them as full cards? Default: denser low-weight strips so the actionable block leads.
3. **Kiosk-only vs shared**: Default: response/size-aware (big at 1–3 m, still correct up close); no separate `kiosk` css toggle unless overload is proven.

---

## Next step

Review/edit this plan — especially the **Screen & flow plan** table, the **module accent map**, and the **three open questions**. When you’re happy (or ask me to apply the defaults), hand this document to Design mode and tell it the option choices (or confirm “use defaults”) so it can start coding against `templates/index.html` + `static/css/main.css` + `static/css/cockpit.css` + `static/js/components/*.js`.
