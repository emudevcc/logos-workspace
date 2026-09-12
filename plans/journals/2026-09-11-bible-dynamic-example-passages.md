---
title: "Dynamic Bíblia example-passage chips: LLM suggestions with a hard validation gate"
date: 2026-09-11
summary: "Replaced 6 hardcoded example-passage chips with an LLM suggester mirroring WordOfDayGenerator, gated by parse_reference; a same-day follow-up documented rather than fixed a pre-existing out-of-range parser gap."
---

# Dynamic Bíblia example-passage chips: LLM suggestions with a hard validation gate

**Date**: 2026-09-11 16:45
**Severity**: Low
**Component**: Bíblia cockpit — example-passage chips (`app/services/bible_examples.py`, `app/api/routes_bible.py`, `static/js/components/bible_study.js`)
**Status**: Resolved

## What Happened

`plans/260911-2228-bible-dynamic-example-passages/` replaced the six
hardcoded example-passage chips in `bible_study.js` (fixed per-language
arrays, same order every load) with a `BiblePassageSuggester` service that
generates a fresh set on each load. The design deliberately mirrors an
existing pattern rather than inventing one: `app/services/word_of_day.py`'s
`WordOfDayGenerator` — LLM-generate via the shared `complete_json` client,
keep a recent-window anti-repeat hint, raise `LLMError` on failure and let
the caller decide what "no output" means. A new `GET
/api/bible/example-passages?language=es|en|pt` endpoint never raises; LLM
failure just yields an empty list, and the frontend's existing hardcoded
array is already the fallback pool, so there is zero user-visible error
path in either direction.

Shipped across three commits: `1f00efd` (backend suggester + endpoint, 20
new tests), `e0558ba` (frontend fetch/fallback/stale-response wiring), and
a same-day follow-up, `a23705e`, that found and documented — but did not
fix — a pre-existing parser gap.

## The Brutal Truth

A bad vocabulary suggestion from Word-of-Day is a shrug. A bad Bible
reference is a broken click: it either 422s in front of a user, or worse,
feeds a slightly-wrong reference straight into the exact LLM exegesis
pipeline the *previous* plan in this repo (`260911-2030-bible-llm-
reliability`) had just spent a whole cycle hardening. So this plan's one
real design decision was refusing to trust the LLM's output shape at all:
every suggested string round-trips through the real `parse_reference()`
before it is ever returned, and anything that raises
`BibleReferenceError` is dropped silently. That gate is the entire reason
this plan doesn't just recreate the fragility the last plan had cleaned up.

And even with that gate in place, the very next pass found a hole in the
thing being trusted to close it: `parse_reference` only enforces *lower*
bounds (chapter ≥ 1, verse ≥ 1). It has no per-book chapter/verse ceiling.
`parse_reference("Juan 99:1")` parses cleanly — John's gospel has 21
chapters — and would happily be served as a clickable chip. That's not a
bug this feature introduced (`bible_parser.py` was last touched in
`afa003d`, untouched by either commit here, and a manually typed "Juan
99:1" behaves identically), but it is a gap this feature now depends on
being small. Fixing it properly needs a 66-book chapter-count table — real
scope, correctly rejected in the plan's own Risk Assessment before this
ever shipped, not discovered after the fact.

## Technical Details

- `_SuggestedPassages` (the Pydantic response model): `passages:
  list[Any]`, not `list[str]`. Deliberate divergence from the plan's
  literal spec — one non-string entry in an otherwise-good LLM response
  would make strict `list[str]` discard the whole response; `list[Any]`
  lets per-item validation (the `parse_reference` gate) do that filtering
  instead of Pydantic doing it all-or-nothing.
- `a23705e` added `test_out_of_range_chapters_still_pass_the_parser`,
  asserting `parse_reference("Juan 99:1").chapter == 99` — pinning the gap
  as an expected result, not a regression, so a future fix has an obvious
  place to update.
- `CHANGELOG.md` "Known gap" section now documents it explicitly: clicking
  such a chip surfaces the normal upstream error, not a crash.
- Backend test count: 268 → 289 across the three commits (20 new in
  `1f00efd`, 1 more in `a23705e`).

## What We Tried

Nothing here was a failed attempt — this is a clean mirror-and-extend job.
The only decision point was whether to expand scope to fix the out-of-range
gap once `a23705e` found it. Rejected: a real fix needs a 66-book
chapter/verse ceiling table, which is new domain data, not new wiring, and
the plan's Risk Assessment had already scoped that out before implementation
started. Documenting-not-fixing was the correct call here specifically
*because* it was anticipated, not because it was inconvenient.

## Root Cause Analysis

The gap exists because `parse_reference` was written to reject obviously
malformed syntax (bad book names, non-numeric chapter/verse, chapter/verse
< 1), not to validate against real per-book verse counts — that was never
its job. This plan is the first caller that puts *machine-generated*
references through it and shows them as one-click affordances, which is a
meaningfully different trust boundary than a human typing a reference they
already believe is real. The parser's original scope was correct for its
original caller; it just wasn't sufficient for this new one, and the plan
correctly recognized that mismatch instead of quietly assuming the parser
would cover it.

## Lessons Learned

1. When validating LLM output that will become a one-click UI affordance
   (not just displayed text), match the validation gate's actual bounds
   checking against what "syntactically parses" versus "is real" means —
   they are not the same thing, and the gap between them is exactly where
   an LLM will occasionally land.
2. `list[Any]` over `list[str]` for partially-trusted LLM JSON output is a
   reusable pattern: let per-item domain validation reject bad entries
   instead of Pydantic discarding a good response over one bad field.
3. Finding a gap and writing it down with a pinning test and a CHANGELOG
   entry is a legitimate close-out action, not a cop-out — but only when
   the gap was already named as accepted risk before the code shipped, not
   invented as an excuse afterward.

## Next Steps

- No immediate owner or deadline: this is an accepted, documented
  limitation, not an open incident. If Bíblia study reports on
  out-of-range chapters start showing up in error logs, that's the signal
  to build the 66-book chapter-count table and tighten
  `parse_reference` — at that point, `Genesis 1:999`-style probes should
  become 422s at generation time instead of at click time.
- 297/297 backend tests, `ruff check` clean, `mypy app` clean (71 files),
  64/64 frontend tests — independently re-verified at close-out, matching
  every commit's own reported gates.
