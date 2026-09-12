---
phase: 1
title: "Backend Favorite Flag"
status: pending
priority: P1
effort: "1.5-2h"
dependencies: []
---

# Phase 1: Backend Favorite Flag

## Goal

Persist a favorite flag per saved study, let the existing studies list be
filtered to favorites only, and add a toggle endpoint to set/unset it.

## Context Links

- `app/core/db.py:60-97` — `MIGRATIONS` tuple, currently 4 entries (schema
  v2 through v5); `app/core/db.py:138-141` applies each in order via
  `PRAGMA user_version`. The next entry is v6.
- `app/schemas/bible.py:94-104` — `StudySummary` (id, reference, translation,
  book_code, created_at) and `StudyRecord(StudySummary)` (adds passage_text,
  report) — adding a field to `StudySummary` reaches both.
- `app/services/bible_studies.py:213-253` — `create_study`'s `INSERT INTO
  studies (...)` explicitly lists columns; the new `is_favorite` column
  needs a `DEFAULT 0` so this INSERT does **not** need to change.
- `app/services/bible_studies.py:330-345` — `list_studies()`: `SELECT id,
  reference, translation, book_code, created_at FROM studies ORDER BY id
  DESC LIMIT 100`, mapped to `StudySummary` field-by-field (not
  `row_factory`-driven `**row`, so every new column must be added to both
  the `SELECT` and the object-construction call explicitly).
- `app/services/bible_studies.py:347-363` — `get_study()`: uses `SELECT *`
  (already gets every column), but still constructs `StudyRecord` field-by-
  field, so `is_favorite` needs adding there too.
- `app/services/bible_studies.py:365-368` — `delete_study()`: the
  `cursor.rowcount > 0` pattern to mirror for the new `set_favorite()`.
- `app/api/routes_bible.py:139-160` — `list_studies`/`get_study`/
  `delete_study` routes; `delete_study`'s 404-on-not-found pattern
  (`routes_bible.py:154-159`) to mirror for the new toggle route.

## Key Insights

- `aiosqlite.Row` supports index/key access but this codebase already
  chose explicit field-by-field construction for `StudySummary`/
  `StudyRecord` (not `**dict(row)`) — follow that existing style rather
  than switching to a different mapping approach partway through the file.
- A boolean in SQLite is stored as `INTEGER` (0/1); `bool(row["is_favorite"])`
  converts it back on read, matching how other boolean-like flags in this
  codebase are handled (there's no existing boolean column in `studies` to
  copy from directly, but `aiosqlite`/SQLite's integer-as-boolean convention
  is standard here).
- `favorites_only` as a **query parameter** on the existing `GET /studies`
  route (not a new path like `/studies/favorites`) avoids a real FastAPI
  routing hazard: `/studies/{study_id}` is registered with an `int` path
  converter, and a literal path segment like `/studies/favorites` competes
  for the same route shape. A query parameter has no such ambiguity and
  needs no route-ordering care.
- The toggle is a single `POST /studies/{id}/favorite` accepting `{"favorite":
  bool}` — one endpoint that sets the flag to whatever the client sends,
  not two endpoints (mark/unmark) or a `DELETE`. The frontend only has
  `apiGet`/`apiPost` (`static/js/lib/api.js`); reusing `apiPost` for the
  toggle avoids needing a third HTTP-verb helper (Phase 2 doesn't need to
  touch `api.js` at all).

## Requirements

- [x] Add migration v6 to `app/core/db.py`'s `MIGRATIONS` tuple:
      `ALTER TABLE studies ADD COLUMN is_favorite INTEGER NOT NULL DEFAULT 0;`
      with a one-line comment matching the existing entries' style (e.g.
      "v6: favorite flag on saved studies, toggled from history/Favoritos").
- [x] Add `is_favorite: bool = False` to `StudySummary` in
      `app/schemas/bible.py` (flows to `StudyRecord` via inheritance).
- [x] Add `FavoriteRequest(BaseModel)` with `favorite: bool` to
      `app/schemas/bible.py`, matching `StudyRequest`'s
      `model_config = ConfigDict(extra="forbid")` convention.
- [x] `list_studies()`: accept `favorites_only: bool = False`; when `True`,
      add `WHERE is_favorite = 1` to the query; add `is_favorite` to the
      `SELECT` column list and to the `StudySummary(...)` construction
      (`bool(row["is_favorite"])`).
- [x] `get_study()`: add `is_favorite=bool(row["is_favorite"])` to the
      `StudyRecord(...)` construction (the `SELECT *` already includes the
      new column, no query change needed there).
- [x] Add `set_favorite(self, study_id: int, favorite: bool) -> bool`,
      mirroring `delete_study`'s shape: `UPDATE studies SET is_favorite = ?
      WHERE id = ?`, return `cursor.rowcount > 0`.
- [x] `routes_bible.py::list_studies`: add `favorites_only: bool =
      Query(default=False)` and pass it through to the service call.
- [x] New `POST /studies/{study_id}/favorite` route, body `FavoriteRequest`,
      calling `set_favorite`; 404 with the existing `"Estudio no encontrado"`
      detail (matching `delete_study`'s message) when the study doesn't
      exist; on success return the updated `StudySummary` (re-fetch via
      `get_study` or have `set_favorite` return the row — simplest: after a
      successful `set_favorite`, call `get_study(study_id)` and return it,
      since the route already has a pattern for "fetch after mutate" adding
      no new query shape).

## Architecture

```
db.py MIGRATIONS  (append)
  # v6: favorite flag on saved studies, toggled from history/Favoritos.
  """
  ALTER TABLE studies ADD COLUMN is_favorite INTEGER NOT NULL DEFAULT 0;
  """

schemas/bible.py
  class StudySummary(BaseModel):
      id: int
      reference: str
      translation: str
      book_code: str
      created_at: str
      is_favorite: bool = False

  class FavoriteRequest(BaseModel):
      model_config = ConfigDict(extra="forbid")
      favorite: bool

bible_studies.py
  async def list_studies(self, favorites_only: bool = False) -> list[StudySummary]:
      where = "WHERE is_favorite = 1 " if favorites_only else ""
      cursor = await self._db.connection.execute(
          "SELECT id, reference, translation, book_code, created_at, is_favorite "
          f"FROM studies {where}ORDER BY id DESC LIMIT 100"
      )
      ...
      StudySummary(..., is_favorite=bool(row["is_favorite"]))

  async def set_favorite(self, study_id: int, favorite: bool) -> bool:
      async with self._db.transaction() as conn:
          cursor = await conn.execute(
              "UPDATE studies SET is_favorite = ? WHERE id = ?",
              (1 if favorite else 0, study_id),
          )
          return cursor.rowcount > 0

routes_bible.py
  @router.get("/studies", response_model=list[StudySummary])
  async def list_studies(request: Request, favorites_only: bool = Query(default=False)) -> list[StudySummary]:
      service: BibleStudyService = request.app.state.bible_studies
      return await service.list_studies(favorites_only=favorites_only)

  @router.post("/studies/{study_id}/favorite", response_model=StudyRecord)
  async def set_favorite(study_id: int, payload: FavoriteRequest, request: Request) -> StudyRecord:
      service: BibleStudyService = request.app.state.bible_studies
      updated = await service.set_favorite(study_id, payload.favorite)
      if not updated:
          raise HTTPException(status_code=404, detail="Estudio no encontrado")
      record = await service.get_study(study_id)
      assert record is not None  # just updated it; can't have vanished mid-request on the single connection
      return record
```

## Related Code Files

- Modify: `app/core/db.py`
- Modify: `app/schemas/bible.py`
- Modify: `app/services/bible_studies.py`
- Modify: `app/api/routes_bible.py`
- Modify: `tests/backend/test_bible.py`

## Implementation Steps

1. Add the v6 migration to `app/core/db.py`.
2. Add `is_favorite` to `StudySummary` and add `FavoriteRequest` to
   `app/schemas/bible.py`.
3. Update `list_studies()`, `get_study()`, add `set_favorite()` in
   `bible_studies.py` per the Architecture block.
4. Update the `list_studies` route's query param and add the
   `set_favorite` route in `routes_bible.py`; import `FavoriteRequest`.
5. Write tests in `tests/backend/test_bible.py`:
   - Migration applies cleanly on a fresh DB (existing DB-setup fixtures
     already exercise the full migration chain on every test run — no new
     fixture needed, just confirm no existing test breaks).
   - `create_study` → `list_studies()` returns it with `is_favorite=False`.
   - `set_favorite(id, True)` → `list_studies(favorites_only=True)` includes
     it; `list_studies(favorites_only=True)` excludes a non-favorited study.
   - `set_favorite` on a non-existent id returns `False`.
   - Route-level: `POST /studies/{id}/favorite` with `{"favorite": true}`
     returns 200 with `is_favorite: true` in the body; on a non-existent id
     returns 404 with the existing "Estudio no encontrado" detail; a
     malformed body (missing `favorite`, or an extra field given
     `extra="forbid"`) returns 422.
6. Run `ruff check app/core/db.py app/schemas/bible.py app/services/bible_studies.py app/api/routes_bible.py tests/backend/test_bible.py`, `mypy app`, `pytest tests/backend -q`.

## Todo List

- [x] Schema v6 migration added
- [x] `StudySummary.is_favorite` + `FavoriteRequest` schema added
- [x] `list_studies(favorites_only=...)`, `get_study` row mapping, `set_favorite()` implemented
- [x] Route query param + new toggle route added
- [x] Tests: favorited-study round-trip, filter inclusion/exclusion, not-found 404, malformed-body 422
- [x] `ruff` + `mypy` + backend suite green

## Success Criteria

- A study created via `create_study` and then favorited via `set_favorite`
  appears in `list_studies(favorites_only=True)` and is excluded from that
  same call before being favorited.
- `POST /studies/{id}/favorite` for a non-existent id returns 404 with the
  same `"Estudio no encontrado"` detail `delete_study` already uses (message
  consistency across the file's existing 404s).
- The full backend suite still passes after the migration is added — every
  existing test's DB setup already runs the full migration chain, so this
  is the regression signal that the `ALTER TABLE` syntax and default are
  correct.

## Risk Assessment

- **Risk:** Forgetting to add `is_favorite` to `list_studies()`'s explicit
  `SELECT` column list (easy to miss since the method already lists 5
  columns by name) would make the new field always default to `False` in
  that response even for favorited studies. **Mitigation:** the test suite
  explicitly asserts a favorited study appears correctly in the *unfiltered*
  `list_studies()` response too, not only the filtered one — catching
  exactly this class of mistake.
- **Risk:** `FavoriteRequest`'s `extra="forbid"` could reject a body the
  frontend sends if Phase 2 accidentally includes an extra field (e.g.
  sending the whole `StudySummary` back instead of just `{"favorite":
  bool}`). **Mitigation:** Phase 2's implementation must send exactly
  `{"favorite": <bool>}`; call this out explicitly in Phase 2's own
  requirements so the two phases agree on the wire shape without needing to
  loosen validation here.

## Security Considerations

- No new user-facing input beyond a boolean and an existing validated
  integer path param (`study_id`, already `int`-typed by FastAPI); no new
  injection surface (parameterized queries throughout, matching every other
  method in this file).

## Next Steps

- Phase 2 wires the frontend to the `favorites_only` query param and the
  new toggle route, and builds the shared list module both `bible_history.js`
  and the new `bible_favorites.js` use.
