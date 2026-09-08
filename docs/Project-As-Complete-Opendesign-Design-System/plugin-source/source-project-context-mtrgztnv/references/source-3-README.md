# English Cockpit OS Design System

An OpenDesign package distilled from the prototype project **Web Prototype**
(`3bebbd17-ade8-4e22-bb46-02b7a90f06fe`). It is a self-contained, reusable design system workspace for
rebuilding English-training dashboard UI on the same look-and-feel.

## Product Overview

**English Cockpit OS** is a self-hosted daily English practice cockpit built to run on a
Raspberry Pi 3B Chromium kiosk (1080p TV, no mouse, `--disable-gpu`, viewed from 1–3 m). The product
presents **four practice modalities** — Today, Practice, Speak, Write — as a single-page dashboard of
**14 accent-coded module cards** (flashcards + SRS grading, a timed PREP drill, verbs & grammar coach,
pronunciation shadowing, voice roleplay with hold-to-talk, a live speech-metrics coach, captioned live
radio, a writing coach, and a five-register swap) plus a shared full-detail modal. It supports live
audio roleplay/reading, keeps a streak + daily-goal ring fed by real API stats, refreshes content on a
schedule, and re-renders module detail deterministically into an HTML `<dialog>`.

The product provides a calm, glanceable-at-a-distance reading experience: quiet Apple-grey dark surfaces,
one system-blue identity hue, **Georgia serif reading surfaces** against tabular mono numerics, and
stroke-SVG interaction icons — engineered frugal enough for a 1 GB, GPU-less device (no perpetual CSS
animations). The design system package captures that visual contract plus the interactive component kit
so new surfaces can be built to match.

Primary surfaces: (1) the **macOS-style side rail** with nav + status foot; (2) the **Today/Practice/
Speak/Write card grids**; (3) the **shared module detail dialog** (Spaced Repetition Flashcards,
Verbs & Grammar, Register Swap, Writing Coach…) with live in-modal controls.

## Package Contents

Core deliverable files and how they map:

- `DESIGN.md` — the visual + interaction contract: product context, color incl. the **14-slot module
  accent map (C2)**, typography, spacing, layout, components, motion, voice and anti-patterns.
- `colors_and_type.css` — color / module-accent / type-stack foundation; paste first.
- `tokens.css` — spacing, radius, elevation, motion, layout tokens; paste second.
- `ui_kits/app/` — applied interface kit (see its README) with a working single-page gallery
  (`index.html`) and modular component recipes under `ui_kits/app/components/`.
- `preview/` — 8 focused review cards (see the Preview Manifest below).
- Preserved source examples at project root (`english-cockpit-os.html` interactive prototype,
  `english-cockpit-uiux-plan.md`, `english-cockpit-implementation.md`).
- `assets/` — extracted 24×24 stroke-SVG icon set (`assets/icons/`).
- `build/` — runtime icon manifest `build/icons.js` (`icon(name)` helper).
- `context/` — `source-context.md` copy manifest + `provenance.md` evidence ledger + local-repo notes
  under `context/local-code/`.

## Source Evidence

Built directly from the saved source project's outputs — the files below are kept verbatim and are the
authority for every token and component in this package:

- `english-cockpit-os.html` — refined UI/UX **prototype** (the only visual rendering, authored as the
  applied reference).
- `english-cockpit-uiux-plan.md` — UI/UX plan: audit (issues A–G), direction, screen plan S01–S07.
- `english-cockpit-implementation.md` — repo implementation guide (C1–C8) carrying the finalized
  **C2 module-accent map** and the card→modal fresh-render contract (C7).
- Linked real repository `/Users/esteban/Documents/code_ai/english_cockpit_os` — summarized in
  `context/local-code/english_cockpit_os.md`.

Full attribution for each token: `context/provenance.md`.

## Preserved artifacts

- `assets/icons/` — 18 generated stroke-SVG files (14 `module-*.svg` + 4 `ui-*.svg`), byte-for-byte
  equal to the prototype's icon paths (verified by script).
- `build/icons.js` — ESM runtime icon manifest (14 module + 4 ui paths + nav aliases).
- `fonts/` — intentionally **omit**ted: the source uses system font stacks (no renders for the kiosk).
- `english-cockpit-os.html` — the preserved interactive source prototype; kept as the applied, live
  reference example (it is the original component reality the package restates).

## Reuse Workflow

To stand up a new surface from this package:

1. Inspect the applied kit first — open `ui_kits/app/index.html` or `english-cockpit-os.html` to see
   the composed shell, grids, and modal in action.
2. Read `DESIGN.md`, then paste `colors_and_type.css` + `tokens.css` into the first `<style>`.
3. Compose from `ui_kits/app/cockpit.css` and reuse the `components/*.html` recipes for isolated states.
4. Load icons from `assets/icons/` (markup) or `build/icons.js` (JS-rendered modules).
5. Keep the contrast + state contract and run against the anti-pattern list (§9 of DESIGN.md).
6. Verify and compose per `SKILL.md`, and complete with the package audit before shipping:
   `"$OD_NODE_BIN" "$OD_BIN" tools connectors design-system-package-audit --path . --fail-on-warnings`.

## Preview Manifest

Review in this order (open `preview/index.html` for a clickable landing):

| Review focus | Card |
|---|---|
| Applied experience (start here) | `preview/../ui_kits/app/index.html` |
| Preserved source prototype | `english-cockpit-os.html` |
| Core colors / semantic states | `preview/colors-primary.html` |
| Module accents + icon set (brand) | `preview/brand-assets.html` |
| Typography specimens | `preview/typography-specimens.html` |
| Spacing & rhythm | `preview/spacing-tokens.html` |
| Radius & elevation | `preview/radius-shadows.html` |
| Component states | `preview/components-buttons.html` |
| Applied UI surfaces | `preview/ui-surfaces.html` |

Reviewers should start with `preview/colors-primary.html` and `preview/brand-assets.html` (color +
tokens), then `preview/typography-specimens.html`, `preview/spacing-tokens.html` and
`preview/radius-shadows.html`, then move to components and applied surfaces; keep `SKILL.md` +
`DESIGN.md` open as the reference.

## Provenance & integrity notes

Two source facts matter up front (full details in `context/provenance.md`): the prototype's demo
numerals (`6 / 20`, `14 new`) are **layout-only** illustrations and are not tokens; and the applied
module hues inside the prototype are an earlier draft — the canonical accent spec is the finalized **C2
map** (kept as the top half of `preview/brand-assets.html`).
