# ui_kits/app — English Cockpit OS applied interface kit

This kit is the **applied** layer of the English Cockpit OS design system: a working, tappable recreation
of the preserved prototype (`english-cockpit-os.html`). It is not a decorative mock — every control below
has real hover / focus / active / armed (recording-live) states, the sidebar nav switches views, and each
module card opens the shared `<dialog>` with a **fresh-rendered** body (contract S07 / C7 of the source).

## Structure

```
ui_kits/app/
  README.md            this file
  cockpit.css          component recipe library (the whole kit, token-driven)
  index.html           gallery: dark shell + 4 views (Today/Practice/Speak/Write)
                       → 14 accent module cards → one shared modal (fresh render)
  components/          five isolated component demos with states
    nav-item.html      macOS sidebar rail (the AppShell "Sidebar")+ 44px targets + status foot
    card.html          badge card + top accent bar + "Open" cue for the 14-module grids
    buttons.html       solid / soft / line / live / grade-choice / choice-pill — one primary per surface
    modal.html         the shared Dialog: mono kicker + serif title + sticky footer (fresh body)
    controls.html      flashcards w/ grading keys 1-4, segmented tabs, phase chips, textarea "InputBar",
                       conversation "MessageBubble" bubbles, metrics clusters
```

`cockpit.css` is copy-paste into new surfaces (after `colors_and_type.css` + `tokens.css`); the
`components/*.html` pages show each recipe in isolation; `index.html` composes them into the real kit.

## Usage

- **Compose a new view**: paste `../../colors_and_type.css` + `../../tokens.css`, then copy the needed
  recipes from `cockpit.css`; reuse the card + modal DOM from `index.html` for the grids/dialog.
- **Bind an accent**: set `style.setProperty("--mc", <hue>)` on each card, or `data-module="<key>"`,
  and keep each *view* distinct (no two identical module hues).
- **Add isolation views**: keep one entry in `components/` per control family so reviewers can load
  focused states without the full shell.
- **Real data only**: numeric cells must render real `/api/srs/stats` / `/healthz` values or an honest
  placeholder — never invented metrics.
- **Icons**: use `../../assets/icons/*.svg` (markup) or `icon()` from `../../build/icons.js` (JS).

## Design notes

- Source basis: `english-cockpit-os.html` (applied reference) + `ui_kits/app/cockpit.css` + the
  finalized C2 accent map kept in `english-cockpit-implementation.md`.
- Layout & surfaces: dark Apple-grey shell → Today leads the actionable "next step"; digests are lighter;
  no horizontal scroll; 44 px targets; one visible focus ring per control.
- Colors/typography/tokens live only in the two top level files — the kit never redefines them.

## Layout cross-map (to the product's real modules)

Today: today · word-of-day · news · podcast · weekly-plan.
Practice: srs · prep (timed drill) · grammar (3-tab Coach) · shadowing (2-tab).
Speak: voice roleplay (hold-to-talk + MessageBubble bubbles) · speech metrics · radio (captioned, with a
live caption **InputBar**/read-along surface).
Write: declutter (Polish / Correct) · register (5-register segmented **Segmented control**).

## Design review entry

Open `index.html`. Suggested review order: **side rail nav + status foot** (nav-item / S01–S02) →
**Today grid** (card / S03) → open **Spaced Repetition Flashcards** and **Grammar** (modal + buttons +
routing) → **Voice roleplay** armed state → **Register Swap** segmented tab. Then scan the isolated
`components/*.html` pages.
