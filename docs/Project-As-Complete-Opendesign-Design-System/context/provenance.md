# Provenance — English Cockpit OS Design System

This design-system package was generated in place from an existing OpenDesign project. Every token,
component rule, copy sample, and anti-pattern below is extracted from the copied source evidence —
nothing is invented.

## Source project

- Source project id: `3bebbd17-ade8-4e22-bb46-02b7a90f06fe`
- Source project name: Web Prototype
- Source kind: `prototype` (single-page web app prototype)
- Linked real repository: `/Users/esteban/Documents/code_ai/english_cockpit_os`
  (FastAPI + Jinja shell + Tailwind v4 + DaisyUI v5 + vanilla ESM + Vite; Raspberry Pi 3B kiosk,
  1080p TV, Chromium `--disable-gpu`, 1–3 m reading)
- Scenario binding snapshot: `4d6397ff-ae55-440d-9526-5a8b2efece04` (plugin `example-web-prototype`)

## Evidence files (kept at project root, unmodified)

| File | Role |
|---|---|
| `english-cockpit-os.html` | Refined UI/UX **design prototype** (652 lines, self-contained). The only visual rendering of the system: shell, nav, status foot, 14 module cards, shared fresh-render modal, inline stroke-SVG icons, tokens. |
| `english-cockpit-uiux-plan.md` | UI/UX plan (English) — the prototype's declared source of truth. Grounded audit (issues A–G), kept direction (macOS-native dark + Kindle-style serif reading stack), screen plan S01–S07, token/state contract, kiosk scale. |
| `english-cockpit-implementation.md` | Implementation guide (Chinese) — the real repo's sole implementation basis. Commit plan C1–C8, the **finalized 14-slot module accent map (C2)**, SVG icon helper plan (C3), 44 px / kiosk scale (C4), a11y (C5), sidebar status foot (C6), card→modal fresh-render (C7), reduced-motion + rail collapse (C8). |

## How the tokens were chosen

- **Neutrals / core accent / type stacks / radius / spacing / component shapes** — taken verbatim
  from the `:root` token block and component CSS in `english-cockpit-os.html` (lines 17–193).
- **Module accent hues** — canonical set is the finalized, contrast-checked **C2 map** in
  `english-cockpit-implementation.md` (section C2, "14 槽定稿映射"). It resolves the cross-view hue
  collisions the audit flagged in the prototype (A/B) and is the contract the repo ships.
- **Known source discrepancy (documented, not resolved):** the preserved prototype demo's `COL` map
  (`english-cockpit-os.html` line 264–266) renders lighter, earlier pastel variants of some module
  hues (e.g. grammar `#8b9bff` vs canonical `#ff375f`, weekly-plan `#6ec9ff` vs `#5e5ce6`). The
  prototype labels itself a layout pass; `english-cockpit-implementation.md` explicitly supersedes it
  ("原型 HTML 不进入仓库…本指南是唯一实施依据"). This package keeps the prototype as the applied
  visual reference and the C2 map as the canonical accent contract, and flags the difference in
  `DESIGN.md` §2.
- **Demo numerals in the prototype** (`6 / 20`, `14 new`, `0:00`, `— WPM`) are explicitly marked
  *illustrative demo values for layout only — never real API output* (prototype header comment).
  They are not part of the token system.

## Assets

- No raster assets (logos, photos, avatars, favicons) or font files exist in the source evidence —
  the product is a dark, text- and icon-forward kiosk UI. `fonts/` is therefore intentionally
  omitted: type relies on system stacks (San Francisco / Segoe UI, Georgia / Iowan Old Style, SF Mono /
  Menlo) for zero render cost on the target hardware.
- All iconography is inline 24×24 stroke SVG in the prototype; it has been extracted 1:1 to
  `assets/icons/*.svg` (24 files) with a runtime manifest in `build/icons.js`.

## Derived files (this package)

```
DESIGN.md  README.md  SKILL.md  colors_and_type.css  tokens.css
assets/icons/*.svg        build/icons.js
ui_kits/app/  (cockpit.css, index.html, components/*.html, README.md)
preview/      (8 focused review cards)
context/      (source-context.md, provenance.md)
```
