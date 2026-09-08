# English Cockpit OS — Design System

> Single source of truth for the visual language. Tokens are extracted from the
> running code (`static/css/main.css`, `static/css/cockpit.css`, `templates/index.html`)
> into [`code/tokens.json`](../code/tokens.json). This doc is the human-readable
> contract; the JSON is the machine-readable bag for the OpenDesign toolchain.

## Principles

1. **macOS-native, dark-first.** A dark "cockpit" surfaces the content; chrome is quiet.
2. **One grey ramp.** Shell (DaisyUI) and component (custom CSS) layers share a single
   neutral scale — no drifting duplicate palettes.
3. **Serif for reading, system sans for UI.** Definitions/briefs/transcripts use a
   book serif; controls and labels use the system font.
4. **Restrained motion.** MagicUI-style effects (spotlight, shimmer, gradient border)
   signal affordance, never distract.
5. **Color as identity, not decoration.** Each module keeps one accent color used only
   as a hairline top bar.

## Token architecture (C2 contract)

The CSS is aligned to a semantic "C2" naming scheme. Crosswalk:

| C2 semantic | Code token(s) | Value | Role |
|---|---|---|---|
| `--bg` | `--bg` / `--color-base-100` | `#1a1a1d` | window background |
| `--srf` | `--surface` / `--color-base-200` | `#242429` | panels, cards, sidebar |
| `--up` | `--surface-2` / `--color-neutral` | `#2d2d33` | raised controls, chips, tab track |
| `--ln` | `--surface-3` / `--color-base-300` | `#3c3c44` | hairline-adjacent hover/active step |
| `--fg` | `--text` / `--color-base-content` | `#f5f5f7` | primary text |
| `--mut` | `--muted` / `--color-muted` | `#a8a8b2` | secondary text (≥ 4.5:1 on `--surface`) |
| `--ln` (border) | `--border` / `--border-strong` | `rgba(255,255,255,.1/.18)` | hairline borders |

## Color tokens

### Semantic
| Token | Value | Usage |
|---|---|---|
| `primary` | `#0a84ff` | primary buttons, active nav, focus, spotlight |
| `primary-strong` | `#0a6dd4` | solid accent fill, primary hover |
| `secondary` | `#64d2ff` | secondary accent |
| `accent` | `#bf5af2` | accent (podcast, weekly-plan) |
| `success` | `#30d158` | correct / positive |
| `warning` | `#ff9f0a` | warn |
| `error` | `#ff453a` | errors / destructive |
| `info` | `#64d2ff` | info |

### Module accents (hairline top bar only)
| Module | Accent |
|---|---|
| Word of the Day | `#0a84ff` |
| News | `#5ac8fa` |
| Podcast | `#bf5af2` |
| Radio | `#ff453a` |
| SRS | `#30d158` |
| PREP | `#ff9f0a` |
| Grammar | `#ff9f0a` |
| Writing Coach | `#ff375f` |
| Voice | `#64d2ff` |
| Speech Coach | `#32d74b` |
| Pronunciation | `#ffd60a` |
| Register | `#ff9f0a` |
| Weekly Plan | `#bf5af2` |
| Today (next step) | `#0a84ff` |

## Typography

| Token | Stack | Usage |
|---|---|---|
| `ui-font` | `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, …` | chrome, labels, controls |
| `reading-serif` | `Georgia, "Iowan Old Style", "Times New Roman", serif` | definitions, briefs, transcripts, shadowing |

Type scale is incidental (driven by component size, not a strict modular scale):
card title `0.95rem/600`, body `~0.9rem`, HUD values `1.5rem/700`, view title `1.15rem/600`.

## Spacing & radii

- **Grid:** 8 px (Tailwind `gap-2` 8 / `gap-4` 16 / `p-5` 20).
- **Sidebar:** `15rem` (240 px).
- **Radii:** cards `12px`, controls/fields/tabs `8px`.

## Components

| Component | Classes | Tokens |
|---|---|---|
| Shell | `.app-shell`, `.app-sidebar`, `.app-main` | `--bg`, `--surface`, `--ln` |
| Nav item | `.nav-item` (+ `.is-active`), `.nav-icon` (SVG stroke) | `--mut` idle, `primary` active |
| Card | DaisyUI `.card` (+ `bg-base-200`, `.magic-spotlight`) | `--srf`, module accent bar |
| Tabs | DaisyUI `.tabs.tabs-box` / `.tab` / `.tab-active` | `--up` track, `--ln` step |
| Button | `.btn`, `.btn-primary` (+ shimmer), custom `.chip` | `primary` / `--surface-2` |
| Badge | `.tag`, `.cockpit-status` | pill, module colors |
| Modal | `<dialog class="modal">` + `.modal-box` | `--surface`, `--radius` |
| Inputs | `.declutter-input`, `.station-select` | `--surface-2`, `--ln`, `--radius-sm` |

## Motion (MagicUI ports)

| Effect | Mechanism | Token/duration |
|---|---|---|
| Spotlight | `.card::before` radial, mouse-tracked `--x/--y` | `rgba(10,132,255,0.16)`, 260 px, fade 0.2 s |
| Shimmer | `.btn-primary::after` sweep | `rgba(255,255,255,0.35)`, 0.8 s |
| Gradient border | `.magic-gradient-border::after` conic, `@property --angle` | `#0a84ff → #bf5af2`, 6 s loop |
| Section fade-in | `.app-view` entry | 0.3 s ease, `translateY(6px)→0` |

## Governance

- **Add a color:** extend `:root` in `cockpit.css` and the matching DaisyUI channel in
  `main.css` (keep the two in sync), then record it here + in `code/tokens.json`.
- **Add a module:** reuse an existing accent color first; a new one only if it earns a
  distinct semantic identity.
- **Never hard-code hex in JSX/JS** — use the token; hard-coded literals get lifted as
  synthetic tokens during extraction.
- **Contrast:** secondary text must stay ≥ 4.5:1 on `--surface` (`--mut #a8a8b2`).
