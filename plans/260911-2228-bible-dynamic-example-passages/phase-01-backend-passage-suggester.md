---
phase: 1
title: "Backend Passage Suggester"
status: pending
priority: P1
effort: "1.5-2h"
dependencies: []
---

# Phase 1: Backend Passage Suggester

## Goal

Add a `BiblePassageSuggester` service that asks the LLM for a handful of
passage references appropriate for a 5–15 verse exegetical study, validates
every one through the real reference parser, keeps a small anti-repeat
window, and serve it via a new endpoint that never surfaces an error — LLM
unavailable or failing just means an empty list, which the frontend (Phase
2) already knows how to handle.

## Context Links

- `app/services/word_of_day.py:352-389` — `WordOfDayGenerator`: the exact
  shape to mirror (`__init__(self, llm)`, `enabled` property, `async def
  generate()` calling `self._llm.complete_json(...)`, a `deque[str]`
  recent-window it appends to and includes in the next prompt as an "avoid
  these" hint, raising `LLMError` on validation failure for the caller to
  catch).
- `app/api/routes_content.py:41-50` — `word_of_day_random`: the route-level
  fallback pattern (`try: return await generator.generate() except
  LLMError: log WARNING, fall through` to a non-LLM path) — this phase's
  route mirrors it, except the "non-LLM path" here is an empty list, not a
  curated pool (Phase 2's frontend owns the curated fallback).
- `app/services/bible_parser.py:51` — `parse_reference(raw, translation="")`
  raises `BibleReferenceError` for anything it can't resolve to a book +
  chapter/verse range; accepts PT/ES/EN aliases and abbreviations
  interchangeably regardless of which language's chips are showing
  (`app/services/bible_parser.py:16-36` builds one alias table from all
  three languages' names per book), so a suggestion doesn't have to match
  the UI's current language script to be valid.
- `app/core/budget.py` / `app/services/llm.py:85-86` — `SpendBudget.consume()`
  fires once per `complete_json` call, shared across every cockpit; keep
  this call's `max_tokens` low (150, well under Word-of-Day's 300 and far
  under a six-section study's 2400) since it's a low-value decorative
  suggestion competing for the same daily budget as real study generation.
- `app/main.py:180` — `app.state.word_of_day = WordOfDayGenerator(llm)`:
  the wiring pattern to copy for `app.state.bible_examples`.
- `app/api/routes_bible.py:19-30` — existing imports and router setup in the
  file this phase adds a route to; `GET /api/bible/books` at line 33-35
  shows the plain-`list[...]`-response-model convention already used here.

## Key Insights

- Word-of-Day's generator doesn't validate its output beyond "non-empty
  expression and definition" (`word_of_day.py:374-375`) because a slightly
  off vocabulary suggestion is harmless. A passage reference is not: an
  invalid one either 422s when clicked or — worse — parses into something
  the user didn't expect. Every suggestion **must** pass through
  `parse_reference()` before being returned; anything that raises
  `BibleReferenceError` is dropped, not surfaced.
- The suggester should ask for *several* passages in one LLM call (e.g. 6),
  not one call per chip — matching the existing chip count and keeping the
  budget cost to one `complete_json` call per suggestion refresh, not six.
- The anti-repeat window belongs in the suggester (like Word-of-Day's
  `_recent` deque), not in the route or the frontend — it needs to persist
  across calls within the process to be useful, and the suggester already
  owns the LLM prompt construction.
- This service does not need to know about the app's three UI languages'
  *book-name scripts* specifically — it needs the LLM to respond in
  whichever language's book names read naturally for that `language` code,
  and `parse_reference`'s cross-language alias table (Key: Context Links
  above) means a suggestion is valid regardless of which script it used.
  Prompt in the target language for a natural-reading chip label, validate
  language-agnostically.
- Mirror `WordOfDayGenerator`'s failure contract exactly: `generate()`-style
  method raises `LLMError` (via `self._llm.complete_json` or an explicit
  raise on "every suggestion failed validation"); the *route* decides what
  "no LLM output" means for the response, not the service.
- **Rate-limiting decision (resolved):** `word_of_day_random`
  (`app/api/routes_content.py:41-50`) — the closest analog, a cheap
  LLM-backed suggestion endpoint hit on every page load/refresh — is **not**
  behind `Depends(rate_limited)`; only user-initiated, expensive actions
  (`/api/bible/study`, `/api/bible/passage`) carry it, and `rate_limiter` is
  one shared per-IP instance (`app/main.py:191`) across every route that
  opts in. Follow the established precedent: this endpoint does **not** use
  `Depends(rate_limited)` either, so a burst of language switches can't eat
  into the same 30/min budget a real study submission needs.

## Requirements

- [x] New `app/services/bible_examples.py` with a `BiblePassageSuggester`
      class: `__init__(self, llm: LLMProvider)`, an `enabled` property
      delegating to `self._llm.enabled`, and `async def suggest(self,
      language: str) -> list[str]`.
- [x] `suggest()` builds a localized (es/en/pt) system prompt asking for 6
      diverse, well-known passages suited to a 5–15 verse exegetical study
      (mix of OT/NT, avoid the same book twice in one response), and a
      per-`language` recent-window `deque[str]` (maxlen 6, matching
      Word-of-Day's `_RECENT_WINDOW`-style constant, though the count can
      differ) rendered into an "avoid these" hint exactly like
      `word_of_day.py:365`. Use one `deque` per language (a
      `dict[str, deque[str]]`), since the three languages' chip sets are
      independent and shouldn't cross-suppress each other.
- [x] The LLM call requests a JSON object with a `passages: list[str]`
      field (`temperature=0.9`, `max_tokens=150`) — not a bare JSON array,
      since `LLMClient.complete_json` requires a top-level object
      (`app/services/llm.py:104-105`).
- [x] Every string in the parsed `passages` list is validated via
      `parse_reference(candidate)` (no translation hint needed — validation
      only cares whether it's parseable); invalid ones are dropped, not
      retried (no corrective retry loop here — this is a low-stakes
      suggestion list, not the six-section study pipeline; a low validated
      count just means fewer chips, handled by Phase 2's fallback).
      Successfully-validated raw strings (as the LLM wrote them, not a
      re-serialized canonical form) are what gets returned and remembered
      in the recent-window.
- [x] If the LLM call raises `LLMError` (not configured, budget exceeded,
      rate-limited, malformed JSON — Phase 1 of the prior plan's typed
      taxonomy already covers all of these), `suggest()` lets it propagate;
      it does not catch and return `[]` itself — that decision belongs to
      the route, matching `WordOfDayGenerator.generate()`'s contract.
- [x] New `GET /api/bible/example-passages` route in `routes_bible.py`,
      query param `language: str = Query(default="es")` validated against
      `{"es", "en", "pt"}` (default to `"es"` for anything else, matching
      `_resolve_language`'s existing fallback convention at
      `routes_bible.py:147-155`), `response_model=list[str]`. On success
      returns the validated list; on any `LLMError` (including
      not-configured) logs at `WARNING` (mirroring
      `routes_content.py:48-49`) and returns `[]`; never raises an
      `HTTPException` from this route.
- [x] Wire `app.state.bible_examples = BiblePassageSuggester(app.state.llm)`
      in `app/main.py`, next to the existing `bible_studies`/`word_of_day`
      wiring.
- [x] This endpoint does **not** carry `dependencies=[Depends(rate_limited)]`
      — matching the resolved decision above (same precedent as
      `word_of_day_random`), not an oversight. Add a one-line code comment
      at the route saying so, so a future reviewer doesn't "fix" it by
      adding the dependency back.

## Architecture

```
app/services/bible_examples.py
  class BiblePassageSuggester:
    def __init__(self, llm: LLMProvider):
      self._llm = llm
      self._recent: dict[str, deque[str]] = {}  # one window per language

    @property
    def enabled(self) -> bool: return self._llm.enabled

    async def suggest(self, language: str) -> list[str]:
      window = self._recent.setdefault(language, deque(maxlen=6))
      avoid = "Avoid: " + ", ".join(window) if window else ""
      raw = await self._llm.complete_json(
          system=_SYSTEM_BY_LANG[language], user=avoid,
          max_tokens=150, temperature=0.9,
      )
      candidates = _SuggestedPassages.model_validate(raw).passages
      valid = []
      for candidate in candidates:
          try:
              parse_reference(candidate)
          except BibleReferenceError:
              continue
          valid.append(candidate)
      for v in valid:
          window.append(v)
      return valid

routes_bible.py
  @router.get("/example-passages", response_model=list[str])
  async def example_passages(request, language="es") -> list[str]:
      lang = language if language in {"es", "en", "pt"} else "es"
      suggester = request.app.state.bible_examples
      try:
          return await suggester.suggest(lang)
      except LLMError as exc:
          logger.warning("Bible example-passage suggestion failed: %s", exc)
          return []
```

## Related Code Files

- Create: `app/services/bible_examples.py`
- Modify: `app/main.py`
- Modify: `app/api/routes_bible.py`
- Create: `tests/backend/test_bible_examples.py`

## Implementation Steps

1. Read `app/services/word_of_day.py:340-389` in full immediately before
   writing `bible_examples.py` — copy its shape (constructor, `enabled`,
   recent-window pattern, `LLMError` propagation), not just its idea.
2. Write `app/services/bible_examples.py`: the `_SYSTEM_BY_LANG` dict (es/en/pt,
   short — this is a much smaller prompt than the six-section study's), a
   `_SuggestedPassages(BaseModel)` with `passages: list[str] =
   Field(default_factory=list)`, and `BiblePassageSuggester` per the
   Architecture block.
3. Add the route in `app/api/routes_bible.py`: import
   `BiblePassageSuggester` isn't needed at the route (only used for the
   `isinstance`-free `try/except LLMError` — reuse the existing `LLMError`
   import already in this file), add the `logger` module-level declaration
   if not already present (check — `routes_bible.py` doesn't currently
   import `logging`; add it).
4. Do not add `Depends(rate_limited)` to this route; add the one-line
   comment noting why (matches `word_of_day_random`'s precedent).
5. Wire `app.state.bible_examples` in `app/main.py` next to the existing
   `word_of_day`/`bible_studies` assignments.
6. Write `tests/backend/test_bible_examples.py` mirroring
   `tests/backend/test_word_of_day.py`'s `test_generator_serves_llm_word_...`
   and `test_generator_avoids_recent_items_in_prompt` shapes:
   - LLM returns a mix of valid and invalid references → only valid ones
     come back.
   - Two consecutive `suggest()` calls for the same language → the second
     call's prompt contains the first call's results in the "avoid" hint.
   - LLM raises `LLMNotConfiguredError`/`LLMBudgetExceeded`/generic
     `LLMError` → `suggest()` propagates it (test at the service level);
     the *route* returns `[]` for the same cases (test at the route/
     `TestClient` level, matching the existing route-level test pattern in
     `tests/backend/test_routes_content.py` if one exists for
     `word_of_day_random` — check and follow it).
   - All suggestions invalid → `suggest()` returns `[]` (not an error).
7. Run `ruff check app/services/bible_examples.py app/api/routes_bible.py app/main.py tests/backend/test_bible_examples.py`, `mypy app`, `pytest tests/backend -q`.

## Todo List

- [x] `BiblePassageSuggester` added, mirroring `WordOfDayGenerator`'s shape
- [x] Per-language anti-repeat window
- [x] Every suggestion validated via `parse_reference`; invalid ones dropped silently
- [x] `GET /api/bible/example-passages` added, never raises, returns `[]` on any `LLMError`
- [x] `app.state.bible_examples` wired in `app/main.py`
- [x] No `Depends(rate_limited)` on this route, with a comment explaining why
- [x] Tests cover: mixed valid/invalid filtering, anti-repeat, all-`LLMError` paths at both service and route level, all-invalid → empty list
- [x] `ruff` + `mypy` + backend suite green

## Success Criteria

- `BiblePassageSuggester.suggest()` never returns a string that
  `parse_reference()` would reject — enforced by construction (every
  returned item already passed the same call), verified by the mixed
  valid/invalid test.
- `GET /api/bible/example-passages` returns HTTP 200 with a JSON array in
  every tested failure mode — never a 4xx/5xx from this route.
- The recent-window test proves the second call's prompt differs from the
  first (the anti-repeat hint is actually being sent, not just stored).

## Risk Assessment

- **Risk:** Sharing the global `SpendBudget` with real study generation
  means every Bíblia cockpit mount/language-switch that triggers a chip
  refresh spends one of the same daily units a real study would use.
  **Mitigation:** `max_tokens=150` keeps the per-call cost small relative to
  a 2400-token study; this is an accepted trade-off matching your explicit
  choice of "LLM-generated each load" (the same cost shape Word-of-Day
  already has for the English cockpit) — not silently reduced, but worth
  restating here since it's a real, shared resource.
- **Risk:** The LLM could return fewer than 6 valid passages (or zero) on a
  given call, especially early on when the anti-repeat window is empty and
  temperature is high. **Mitigation:** this is fine by design — Phase 2's
  frontend fills any gap with the existing curated array; the service
  doesn't need to guarantee a count.
- **Risk:** A suggestion could validate as parseable but resolve to a
  passage far outside the intended 5–15 verse guidance (e.g. "Salmos 119",
  176 verses) — `parse_reference` doesn't enforce a verse-count bound (see
  the prior plan's scouting: no such check exists in the parser today).
  **Mitigation:** state the 5–15 verse guidance explicitly in the system
  prompt (the model can follow it even though the parser doesn't enforce
  it); do not add new verse-count validation logic to the parser itself —
  that's a pre-existing gap affecting manually-typed references too, out of
  this plan's scope.

## Security Considerations

- No new user input surface: `language` is validated against a fixed set,
  same pattern as `_resolve_language` elsewhere in this file.
- No new logged content beyond a `WARNING` on suggestion failure, which
  should truncate the logged exception message to ~200 characters, matching
  the convention `app/services/llm.py`'s `_truncate()` helper established —
  `_truncate` is module-private, so inline an equivalent `str(exc)[:200]`
  here rather than importing a private name across modules.

## Next Steps

- Phase 2 wires the frontend to call this endpoint and fall back to the
  existing curated array.
