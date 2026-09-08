# English Cockpit OS — Design System

> Category: Project Design System
> Surface: web (dark kiosk dashboard, 1080p)
> Derived from OpenDesign source project "Web Prototype" (`3bebbd17-ade8-4e22-bb46-02b7a90f06fe`)

**One sentence:** A macOS-native dark, glanceable-at-1–3 m English-practice dashboard — quiet Apple-grey
surfaces, one system-blue identity hue with 14 per-module accents, system sans-serif chrome over a
Kindle-style Georgia serif reading stack and tabular mono numerics — engineered to stay calm and cheap
on a 1 GB RAM Raspberry Pi 3B kiosk with `--disable-gpu`.

---

## 1. Product Context · Visual Theme & Atmosphere

Product context: **English Cockpit OS** is a self-hosted daily English cockpit shown on a living-room TV /
monitor (1080p Chromium kiosk, no mouse, keyboard-first, `--disable-gpu`). It mixes four practice
modalities — Today, Practice, Speak, Write — each surfacing 2–5 module cards that open into a shared
dialog. The UI text is calm, precise English.

Mood: **macOS-native dark** (System-style greys, traffic lights, translucent-lite hairlines) crossed with
**Kindle reading surfaces** (serif definition cards, conversation transcripts, coach textareas). The
result reads as *shipped desktop software for a room*, not a marketing page: quiet, dense but airy,
hierarchical, zero decoration for its own sake. One decisive flourish is kept — the fade-in of content —
while GPU-driven effects (spotlight, shimmer, rotating gradient border) are explicitly out of scope for
this kiosk target and must be gated behind `(pointer:fine)` + no-reduced-motion if ever reintroduced.

### Evidence-backed direction (kept from source)
- No palette or type rebuild — refine the existing system (`english-cockpit-uiux-plan.md` → *Direction*).
- Reusable DaisyUI `cockpit` theme vars were the repo platform; this package exposes the same values as
  plain CSS custom properties in `colors_and_type.css` + `tokens.css`.
- Single source of truth for tokens; no parallel legacy `:root` copies, no dead accent maps (audit items A–B).

---

## 2. Color

Palette derives **only** from the source evidence. Base neutrals and the blue system accent are the
prototype `:root` tokens (verbatim); module hues are the finalized C2 contract. All variants are derived
in `oklch()` / `color-mix()` by the state rules in §7 — never hand-picked hex.

### Core surfaces & text (dark)
| Token | Hex | Role / contrast rule |
|---|---|---|
| `--bg` | `#1a1a1d` | page background |
| `--srf` | `#242429` | rail, cards, dialog panel |
| `--up` | `#2d2d33` | elevated fills: textarea, cardface, metrics, conversation "them" bubble |
| `--ln` | `#3c3c44` | hairline borders & dividers |
| `--fg` | `#f5f5f7` | primary text on `--srf` |
| `--mut` | `#a8a8b2` | secondary text — **≥ 4.5:1** on `--srf` |
| `--faint` | `#9696a0` | tertiary / kicker text, ghost icons — small text never below 4.5:1 where used |

### Identity + states
| Token | Hex | Role |
|---|---|---|
| `--acc` | `#0a84ff` | system blue — nav active, goal ring, focus ring, primary identity. Appears ≤ twice per screen. |
| `--acc-t` | `#2f9bff` | accent-as-text on dark (links, values) — ≥ 4.5:1 |
| `--acc-d` | `#0a6dd4` | deep accent fill for solid primary buttons — white text ≥ 4.5:1 (~4.7:1) |
| `--acc-dh` | `#085eb6` | same, hover (darker, not lighter) |
| `--ok` | `#30d158` | online / success / correct |
| `--live` `--live-h` | `#ff3b30` / `#e02e24` | recording / live-listening armed state + hover |
| Traffic lights | `#ff5f57` `#febc2e` `#28c840` | decorative macOS window dots |

### Module accent system — finalized 14-slot map (C2)
All 14 hues are mutually distinct; hard constraint is **distinctness within one view**, reuse across
views is allowed. Each module binds `--mc` (see `[data-module]` rules in `colors_and_type.css`).

| view | module | accent | notes |
|---|---|---|---|
| Today | today | `#0a84ff` | the one blue in the system identity |
| | word-of-day | `#ff9f0a` | yellow-family: decoration/large only |
| | news | `#5ac8fa` | |
| | podcast | `#bf5af2` | |
| | weekly-plan | `#5e5ce6` | indigo — ceded `#bf5af2` to podcast |
| Practice | srs | `#30d158` | |
| | prep | `#ffd60a` | yellow-family: decoration/large only, never <14px text |
| | grammar | `#ff375f` | pink-red — ceded `#ff9f0a` |
| | shadowing | `#64d2ff` | light blue — ceded `#ffd60a` |
| Speak | voice | `#00c7be` | teal — ceded `#64d2ff` |
| | speech | `#32d74b` | |
| | radio | `#ff453a` | red — ceded `#ff375f` |
| Write | declutter | `#ff6482` | light pink |
| | register | `#af52de` | deep violet — ceded `#ff9f0a` |

**Usage contract (source C2):**
- `--mc` / module hue → **decoration only**: card top bar, ≥12px glyph, selected surface, active tab underline.
- Live text, links, and numeric values in a module hue → a **bright variant ≥ 4.5:1** on dark (like
  `--acc-t` for blue). Derive by raising `L` in `oklch()`, same hue/chroma.
- Solid buttons in a module hue → a **deep variant** so white label stays ≥ 4.5:1 (like `--acc-d`).
  Derive by lowering `L`. Yellow-family hues are banned on light fills.
- Accent never appears more than twice per screen; the shared modal uses only its module's `--mc`
  on the kicker + active tab.

### Source discrepancy (documented)
The preserved prototype (`english-cockpit-os.html`, `COL` map) demoed lighter pastel shades of several
module hues (e.g. grammar `#8b9bff`, weekly-plan `#6ec9ff`, prep `#1bc8cd`, register `#9aa6ff`). The
implementation guide supersedes it with the finalized C2 map above ("定稿映射…全部互异"). Both files are
kept as evidence; C2 is the contract, the prototype the applied visual reference. See
`context/provenance.md`.

---

## 3. Typography

Three-stack system (per prototype tokens); display type is the **system UI sans**, body/reading is
**serif**, numerics are **mono tabular**. The two visible families (sans chrome + serif reading) are
distinct by design; mono is reserved for data.

| Role | Stack (token) | Use |
|---|---|---|
| UI / display | `--font-ui`: `-apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif` | chrome, nav, titles, buttons, labels |
| Reading | `--font-serif`: `Georgia, "Iowan Old Style", "Times New Roman", serif` | flashcards, word definitions, sentences, coach textareas, conversation bubbles, modal titles |
| Numeric | `--font-mono`: `ui-monospace, "SF Mono", Menlo, monospace` — always `tabular-nums` | KPIs, timer/countdown, speech metrics, IPA, day labels, kickers |

> `fonts/` is intentionally omitted — system stacks only, per zero-render-cost kiosk constraint.

### Scale (kiosk 1080p @1–3 m; still fine at arm's length)
| Token | Size / weight / tracking | Where |
|---|---|---|
| `--fs-hero` | 30px · 730 · −.02em | view title (h1) |
| `--fs-display` | 22px · 640 · −.01em | modal title (h2, serif) |
| `--fs-title` | 21px · 660 · −.01em | card title (h3) |
| `--fs-lg` | 17px · 560 | nav item, conversation text |
| `--fs-body` | 16px · 400 | base body, list rows |
| `--fs-btn` | 15px · 620 | buttons |
| `--fs-sub` | 14.5px | view subtitle, word subline |
| `--fs-sm` / `--fs-xs` | 13px / 12px | captions, list meta, micro labels |
| `--fs-kicker` | 11px · 600 · `.11em` uppercase, mono | modal kicker (module mode) |
| `--fs-face` | 30px · serif | flashcard / prompt face (cardface) |
| `--fs-count` | 34px · 720 | PREP countdown |
| `--fs-metric` / `--fs-kpi` | 28px / 24px · mono 680 | metrics / card KPIs |

Rules: body ≥16px for reading surfaces, ≥14px for component small text, headings ≥20px; never rely on
sub-14px text for information the user must act on. Numeric-heavy areas always mono + tabular so
counters don't jitter. No font files ship; never introduce a webfont into the kiosk bundle.

---

## 4. Spacing

Evidence-based tokens in `tokens.css`; rhythm is **compact-desktop with air on the actionable block** —
not a dense web dashboard and not a sparse marketing page.

- Gap ladder: 2 / 4 / 5 / 6 / 8 / 9 / 10 / 11 / 12 / 13 / 14 / 16 / 18 / 20 / 22 / 24 px.
- Semantic gaps: `--gap-xs` 6 (icon+label), `--gap-sm` 9 (button groups, bubbles, list dividers),
  `--gap-md` 13 (badge+title row), `--gap-lg` 18 (grid gutter, dialog body stack), `--gap-xl` 24 (KPIs).
- Paddings: card 18 · dialog body 22 · rail `20px 14px` · main `22px 24px 52px` · button `9px 16px`.
- Radius ladder: 8 (icon-btn hit box) · 11 (buttons/nav) · 13 (badge/foot panel) · 14 (cards, cardface,
  textareas, bubbles, metrics) · 18 (dialog panel) · `999px` (pill: status, chips).
- Elevation: dialog `0 30px 90px rgba(0,0,0,.6)` over `rgba(10,10,12,.6)` backdrop + 2px blur.
  Cards use **borders, not shadows** (1px `--ln`; hover `--card-line-h`).
- Targets: minimum 44px hit height for every control; card icon badge is a fixed 44px square.

---

## 5. Layout & Composition

Single-page app, **4 views** (Today / Practice / Speak / Write), one shared dialog. There are no
separate routes — the active view persists via `localStorage`.

- **Shell**: fixed 276px left rail (`--rail-w`) + fluid main. Rail: traffic lights → brand → 4 nav
  items → status foot pinned bottom (`margin-top:auto`). Main: view header (title + subtitle), status
  pill, then the card grid; scrolls internally; `main` min-width 0 — **no horizontal scroll ever**.
- **Grids**: `g3` = 3 equal columns for Today/Practice/Speak; `g2` = 2 columns for Write (bigger
  working surfaces). Gutter 18px. Collapse: `≤1200px` g3→2 cols; `≤840px` g3→1 col; `≤760px` rail
  collapses to 84px icon rail (hide traffic/brand/status-foot + nav labels, center icons).
- **Today hierarchy**: the actionable block ("next step" + goal numbers) leads; word-of-day and the
  digest strips follow in lighter weight. Cards do not all look alike — uniform shell, varied emphasis.
- **Card ≡ one tap → modal**: whole card clickable (`role="button"`, `tabindex=0`, Enter/Space opens).
- **Dialog (shared, S07)**: DaisyUI-style `<dialog>` `min(880px,94vw)`, `max-height 88vh`; header
  (mono kicker + serif title + close), scrollable body, sticky footer with one primary. Body content is
  **fresh-rendered on each open** — the live DOM is never moved into/out of the dialog (implementation
  guide C7 contract).
- Breakpoints and collapse behavior are part of the layout contract; a 1080p panel must fit fully.

---

## 6. Components

All component recipes live in `ui_kits/app/cockpit.css` and are demoed in `ui_kits/app/`; shapes mirror
the prototype 1:1.

| Component | Anatomy & states |
|---|---|
| **Nav item** (`button.nav`) | 20px stroke SVG + 17px label, row padding to ≥44px hit, radius 11. Idle: `--mut` text. Hover: `--hover-soft` bg + `#fff` text. Active (`is-active`/`aria-current`): `--nav-on` fill + white text, icon stroke `--nav-on-ic` — never opacity-only. Focus ring visible. |
| **Status foot** (sidebar) | Hairline panel (radius 13): greeting row (bolt icon + "Good morning"), then daily-goal ring (42px SVG, stroke `--acc`, `dashoffset = c·(1−done/goal)`) + two-line label: `<b>6 / 20</b>` mono 18 over `<i>Daily goal · reviews done</i>` 13 — **never word-glued**. Refresh countdown sits behind the ⟳ icon's label (title/aria). Real API values only. |
| **Status pill** | Inline-flex pill in view header: 8px dot + uppercase 12px tracking label; online = `--ok` text/border. |
| **Card** (`article.card`) | `--srf` fill, 1px `--ln` border + **3px top accent bar** in `--mc`; radius 14; padding 18; cursor pointer. Header row: 44px badge (accent-tinted 12% fill, stroke icon in `--mc`) + title 21 + kicker (module mode, faint 12). Body: summary copy or KPI cluster; footer cue `Open ↗` (arrow) that brightens on hover. Hover: border → `--card-line-h`; active: `translateY(1px)`. |
| **Buttons** | Min-height 44, radius 11, 15px/620. Variants: `solid` (deep fill `--acc-d`, white, hover `--acc-dh`), `soft` (`--hover-mid`, hover `--hover-strong`), `line` (1px `--ln`, hover border `--hover-line`), `live` (`--live`, hover `--live-h`, used while armed). Picked/choice: `--focus-ok` fill + `--focus-ok-t`. One primary per card/screen; focus ring never blends into the same-hue fill (blue solid uses white ring). |
| **Chips (review pills)** | Radius pill, 13px/600: new = green tint (`--chip-ok-bg`/`--chip-ok-t`), review = yellow tint (`--chip-rev-bg`/`--chip-rev-t`). Decorative context labels only. |
| **Tabs** (`[data-tabs]`) | Top hairline group, 15px/600; active tab: white + 2px `--mc` underline (`margin-bottom:-1px`); keyboard focusable. Drives panes (`data-step` ↔ `data-pane`). Register Swap uses the same control as a 5-segment selector. |
| **Flashcard face** (`.cardface`) | Serif 30px centered on `--up` with hairline; gap blank + accent fill for cloze; IPA line below in mono 14 `--mut`. Flip shows back; grading band 1–4 (Again/Hard/Good/**Easy** primary), keyboard 1–4. |
| **Conversation** (`.conv`/`.co`) | Serif 17px bubbles, max 78%; "them" on `--up`, left; "me" on `--me-bubble`, right, text `--me-bubble-t`; "(hold to talk)" hint in faint sans. |
| **Metrics / KPI clusters** | Mono tabular numerals over faint 12px captions; `--metc` grid (3-up) or `--kpis` inline (gap 24). Countdown large (`--fs-count`) tabular mono. |
| **Textarea (`.ta`)** | Serif 16, `--up` fill, hairline, radius 12, 1.6 line-height; focus ring `--acc`; `disabled` = opacity .55 + faint bg (only allowed contrast reduction); placeholder `--mut`. |
| **List rows** (`.list`) | 16px rows separated by top hairline; mono accent column for day/word labels (`--wl`, `--acc-t`); inline `b` head + faint meta. |
| **Dialog (`.panel`)** | radius 18, `--shadow-dialog`; header/kicker/title + close (44px hit); body gap 18; footer right-aligned; Esc + backdrop dismiss; body fresh-rendered per open; close returns focus. |

---

## 7. Motion & Interaction

Kiosk-frugal contract (source C4, C8 + craft rules):

- **Defaults**: no perpetual animation. Only content fade-in is kept as the system's one flourish.
  Spotlight, shimmer sweep, and rotating gradient border are dropped / gated behind
  `@media (pointer:fine)` **and** no-reduced-motion; kiosk users are never charged for GPU effects.
- **Transitions**: 0.12–0.13s `ease-out` on background/border/color changes only.
- **State pairs (never lighten the foreground)**: hover/focus/active move the **background** —
  white-alpha steps `.05 → .08 → .14`, or OKLch `L` ±0.06–0.12 on colored fills; borders step to a
  stronger hairline; foreground text only ever goes *toward* `#fff`, never toward `--mut`/`--faint`.
  Solid buttons darken their fill on hover (e.g. `--acc-d` → `--acc-dh`, `--live` → `--live-h`) —
  foreground stays white.
- **Focus**: one visible ring per control, `2px solid` at 2px offset; accent ring on dark fills (cards
  use `--mc`), white ring on blue/colored solid buttons; `:focus-visible` only.
- **Disabled** is the only state allowed to reduce contrast (opacity .55 + faint fill).
- **Reduced motion**: `@media (prefers-reduced-motion: reduce)` kills every transition/animation
  (already shipped in tokens.css).
- Modal interactions: Esc + backdrop dismiss; grading keys 1–4 and Space-to-flip active only while the
  dialog is open; armed press controls toggle `aria-pressed` and swap label to `● Recording…` /
  `● Live…` — state is both visual and semantic.

---

## 8. Voice & Brand

- **Language**: quiet, precise English UI copy (existing tone). Sentence-style labels, first-person
  framing for the learner's own actions ("Study next card", "Record your reply", "Add to review").
- **Product voice**: a calm coach, not a gamification engine — "Lead with the review you owe, then warm
  up lightly. Nothing is forced."
- **Kickers** state the learning mode in a mono uppercase micro-label (`MODE`: next step · spaced
  repetition · timed drill · repeat + score · live metrics · 5 registers…).
- **Status language**: online/offline pill; "Daily goal · reviews done" reads as its own line
  (never "6/20reviews done").
- **Truth contract**: numeric cells come from the real API (`/api/srs/stats`, `/healthz`) — no invented
  metrics, no demo numbers in shipped UI. Modal copy may quote live transcript/prompt data only.
- Confirmation pattern is a short verb + ✓ ("Week generated ✓", "Asked ✓", "Rewritten ✓", "Polished ✓")
  that reverts after ~1.4s.
- Icons are stroke SVGs (`stroke="currentColor"`, 24 viewBox, ~1.8 stroke); functional emoji are banned;
  text glyphs `→` / `↗` / `✕` survive only as inline affordance text, not as icons.

---

## 9. Anti-patterns

Everything below is grounded in the source audit (issues A–G) or the system's hard rules — do not
regress into these:

1. **Two parallel style systems / dead token copies** — one palette source (`colors_and_type.css` +
   `tokens.css`); no legacy `:root` hex duplicates, no second `.cockpit-*` accent map, no duplicated
   `.traffic-lights` rules.
2. **Same hue for two modules in one view** (e.g. two cards both `#bf5af2` / `#ff9f0a`) — the C2 map
   above is fixed; if a module set changes, re-check within-view distinctness.
3. **Emoji as functional icons** (`🔊` `🔥` `🎤` `✅` `💡`) — replace with the stroke-SVG set
   (`assets/icons/`, `build/icons.js`); emoji never drives an action.
4. **Low-contrast accent text** — `#ffd60a` / `#ff9f0a` at small sizes, or yellow-family fills under
   white text; yellow-family hues are decoration/large-only. Live text in a module hue uses its bright
   ≥4.5:1 variant; solid buttons use the deep variant.
5. **Opacity-only active states** — nav "on" must stay a filled accent surface + white text; disabled is
   the only contrast-reducing state.
6. **Sidebar-foot crowding / word gluing** at `--rail-w` — "6 / 20" and "reviews done" are separate
   blocks; countdown lives behind the refresh icon; numbers are tabular mono.
7. **Equal-weight Today cards** — the actionable "next step" must lead; digests are lighter strips;
   cards keep varied emphasis inside a uniform shell.
8. **Perpetual GPU/pointer effects on a kiosk** — no 6s gradient borders, mouse spotlight, or shimmer
   without fine-pointer + reduced-motion gates; keep the fade-in only.
9. **Live-DOM relocation into the dialog** — opening a module means **fresh-render** its full view into
   the dialog body and dropping it on close (with `dispose()` for timers/WS/audio). Never `appendChild`
   the card's slot in and out.
10. **Click-to-translate swallowing chrome** — the global dictionary handler must exclude nav, tabs,
    toolbars, buttons, inputs, and all pre-created affordances.
11. **Layout leaks on 1080p** — no horizontal scroll, no clipped/overflowing text, no accidental
    overlaps; cards' serif faces and rows must fit their columns.
12. **Orphaned final lines** — headings and serif reading lines must not strand 1–2 characters; fix
    container/measure, never `white-space:nowrap` into neighbors or `overflow:hidden` concealment.
13. **Light text on light fills / dark on dark** in hover-focus-active pairs — recheck each state pair;
    hover never lightens foreground toward the background.
14. **Decor accent ≠ content color**: `--mc` decor may render at full hue, but any *meaningful* small
    text in that hue must pass 4.5:1 (or 3:1 for large/icon).

---

## Tokens & files (binding)

- Colors, module accents, type stacks & scale → `colors_and_type.css` (paste first).
- Spacing, radius, elevation, motion, layout dimensions → `tokens.css` (paste second).
- Component recipes → `ui_kits/app/cockpit.css` (copy per-component as needed).
- Icons → `assets/icons/*.svg` + `build/icons.js` (runtime helper with the source path data).
- Applied reference → `english-cockpit-os.html` (preserved prototype) and `ui_kits/app/index.html`.
- Evidence & provenance → `context/source-context.md`, `context/provenance.md`.
- Agent usage contract → `SKILL.md`; package overview → `README.md`.
