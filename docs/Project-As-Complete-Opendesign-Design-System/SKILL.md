---
name: English Cockpit OS design system
description: Reuse the English Cockpit OS dark kiosk dashboard design (tokens, module-accent system, applied UI kit) from source evidence in this workspace.
version: 1.0.0
user-invocable: true
---

# SKILL — Build on the English Cockpit OS Design System

> A dark, macOS-native, kiosk-reading **English-practice dashboard**. Dark surfaces, serif reading,
> mono numerics, 14 unique module accents, one shared modal. This skill tells an agent exactly how to
> reuse the package and where every token came from.

**What's inside:** the reusable token, component and preview layers of this package —

- **`DESIGN.md`** — the full contract (context, color incl. the 14-accent map, typography, spacing,
  layout, components, motion, voice, anti-patterns).
- **`colors_and_type.css`** + **`tokens.css`** — the token foundations (color, type, spacing, radius,
  elevation, motion, layout dims); no design time goes past these.
- **`preview/`** — focused review cards: colors, brands & accents, typography, spacing, radius,
  components, applied UI surfaces.
- **`ui_kits/app/`** — an applied **components/** set + an avigation-ready single-page gallery.
- **`assets/icons/`** + **`build/icons.js`** — the preserved 24×24 stroke-SVG icon asset + runtime helper.

**Source context:** built from the saved OpenDesign source project "Web Prototype"
(`3bebbd17-ade8-4e22-bb46-02b7a90f06fe`).
Evidence files in this workspace are kept verbatim and are the ground truth:
`english-cockpit-os.html` (#prototype), `english-cockpit-uiux-plan.md` (#plan, screen plan S01–S07) and
`english-cockpit-implementation.md` (#C1–C8 commit guide with the finalized C2 accent map), with a local
repo summary in `context/local-code/english_cockpit_os.md`. Every token is traced in
`context/provenance.md`.

**When to use this skill:** use it when building or reviewing interfaces, prototypes or UI artifacts
that must match English Cockpit OS — English-module card grids, a dark kiosk reading dashboard, series
detail dialogs, or any component that must reuse the same hue/state/voice. It also checks whether an
existing surface still obeys the contract before production.

### Required reads (read before building)

1. `README.md` (overview + preview manifest).
2. `DESIGN.md` — the full palette, module accent map, type scale, layout, components, motion, voice,
   anti-patterns.
3. `colors_and_type.css` (paste first) and `tokens.css` (paste second).
4. `english-cockpit-os.html` — the interactive preserved applied reference.
5. `ui_kits/app/*.html` + `ui_kits/app/components/*.html` for isolated component states.
6. `context/provenance.md` for token attribution.

**How to use:**

1. **Set the tokens**: prepend `colors_and_type.css` then `tokens.css` verbatim into the first `<style>`.
2. **Import components**: copy recipes from `ui_kits/app/cockpit.css`; for whole screens reuse the
   `ui_kits/app/index.html` DOM (shell → card grids → modal) instead of writing from scratch.
3. **Bind identity + accent**: set a module's hue with `style.setProperty("--mc", <hue>)` or
   `data-module="<key>"` (+ the `[data-module]` rules in colors_and_type.css); keep within-view
   distinctness and the ≤2-per-screen rule.
4. **Use icons**: `assets/icons/` in markup, `icon(name)` from `build/icons.js` for JS-rendered surfaces.
5. **State contract**: hover/focus/active shift the background (never the foreground towards
   `--mut`/`--faint`); one visible `:focus-visible`; disabled is the only contrast-reducing state.
6. **Compose the dialog**: open a module by **fresh-rendering** its full view into the `<dialog>` body
   (never move the live DOM node); Esc + backdrop + Done dismiss; return focus on close.

**Design-system highlights:** what makes this package stick for reviewers —

- **Colors**: Apple greys on dark + one identity blue `#0a84ff`; 14 unique module accents with a
  strict decor-vs-text-vs-fill role rule (C2 map). Live text uses ≥4.5:1 variants; solids use deep fill.
- **Typography / spacing / radius**: sans chrome, Georgia serif reading, tabular mono numerics; kiosk
  scale; evidence-derived gap/radius tokens.
- **Icons / interaction**: currentColor stroke SVG set; 44 px targets; button + modal state pairs;
  motion that never costs a GPU-less kiosk.

## Anti-pattern checklist (regression watch)

Duplicate parallel token copies · two same-hue modules in one view · emoji as functional icons ·
low-contrast accent text / yellow fills under white text · opacity-only active nav · sidebar status-foot
word-gluing · equal-weight Today cards · perpetual GPU effects · live-DOM modal relocation ·
click-to-translate swallowing chrome · clipped/orphaned text or horizontal scroll.

## Preserved files must not be edited

`english-cockpit-os.html`, `english-cockpit-uiux-plan.md`, `english-cockpit-implementation.md`, and
`context/*.md` are immutable evidence. Changes belong in the derived package files (`ui_kits/`,
`preview/`, `DESIGN.md`, etc.).

## Definition of done

Run the package audit until error- and warning-free, with `--fail-on-warnings`:
`"$OD_NODE_BIN" "$OD_BIN" tools connectors design-system-package-audit --path . --fail-on-warnings`
