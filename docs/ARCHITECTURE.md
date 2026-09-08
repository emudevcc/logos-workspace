# Architecture

## Goals

English Cockpit OS is an **English immersion + rapid-practice dashboard** for an
advanced (B2 → C1/C2) learner. It runs 24/7 on a **Raspberry Pi 3B** (1 GB RAM,
quad Cortex-A53) driving a secondary display in Chromium kiosk mode.

Hard constraints that shaped every decision:

1. **1 GB RAM, weak ARM cores** — no local models, no worker pools, no per-request churn.
2. **External inference only** — Groq (LLM) and Deepgram (STT). The Pi never runs a model.
3. **Zero-build frontend** — vanilla HTML/CSS/ES modules, served as-is.

## Design principles

- **One process, one worker.** Each uvicorn worker duplicates the interpreter and
  caches, so the app runs as a single async worker. Everything heavy is created
  once in the lifespan and shared via `app.state`.
- **Shared resources, no churn.** One `aiosqlite` connection (WAL), one
  `httpx.AsyncClient` (connection pool), one WebSocket registry.
- **Pure logic is testable.** The SM-2 engine, connector detection, and frontend
  helpers are free of I/O/clock and unit-tested in isolation.
- **Graceful degradation.** When an external API is unconfigured or failing,
  features degrade (empty vocab, summary fallback, empty transcript) instead of
  crashing the dashboard.
- **Deterministic where possible.** Facts that never change — irregular verbs,
  minimal pairs, pronunciation pitfalls, grammar rules, monologue topics — are
  curated in `app/services/*.py` and served with zero LLM cost or hallucination.
  Only genuinely generative work (drills, coaching, writing, speaking feedback,
  planning) calls the LLM, always rate-limited and budgeted.

## Process & resource model

```
        ┌───────────────────────────── uvicorn (single worker) ─────────────────────────────┐
        │                                                                                    │
Browser ─┤  FastAPI app                                                                      │
        │   ├─ app.state.http        shared httpx.AsyncClient (pool: 10 conn, keepalive 5)  │
        │   ├─ app.state.db          one aiosqlite connection (WAL + write lock)            │
        │   ├─ app.state.llm         Groq client (retry + JSON mode + spend budget)         │
        │   ├─ app.state.deepgram    STT client (Deepgram or local whisper.cpp)            │
        │   ├─ app.state.news/podcast/...  content services (TTL-cached)                    │
        │   ├─ app.state.grammar_drill/writing/monologue/plan  LLM drill & coach services   │
        │   ├─ app.state.ws_manager  WebSocket registry + heartbeat task                    │
        │   └─ app.state.rate_limiter / budgets                                             │
        └────────────────────────────────────────────────────────────────────────────────────┘
                    │ HTTP + WebSocket            │ httpx (Groq / Deepgram / RSS)
                    ▼                             ▼
              static/ + templates/           external APIs (no local models)
```

Key points:

- `app/main.py` exposes `create_app(http_client, llm, deepgram)` so tests can inject
  fakes; the module-level `app = create_app()` is the production instance.
- The lifespan creates the DB (and seeds the default deck), the WS manager, and
  starts the heartbeat task; it tears all of them down on shutdown.
- `python -m app` (`app/__main__.py`) is the entrypoint; it binds `127.0.0.1` by default.

## Persistence & concurrency

- **SQLite (WAL)** via `aiosqlite`, a single connection for the process lifetime.
- Writes are serialized by an `asyncio.Lock` inside `Database.transaction()`,
  which wraps `BEGIN IMMEDIATE` … `COMMIT`/`ROLLBACK`. This makes read-modify-write
  operations (like SRS review) atomic.
- All persisted timestamps use one canonical format — `YYYY-MM-DDTHH:MM:SSZ`
  (`app/core/timeutil.py`) — matching the SQLite `strftime` defaults so lexicographic
  `due_at` comparisons are correct.
- Schema changes are versioned via `PRAGMA user_version`: the baseline schema is
  version 1, and future migrations are appended to the `MIGRATIONS` tuple in
  `app/core/db.py` and applied in order on startup.

### Schema

- `decks(id, slug, name, description, created_at)`
- `cards(id, deck_id, front, back, ipa, register_tag, examples[JSON], ease_factor,
  interval_days, repetitions, due_at, created_at, updated_at)`
- `reviews(id, card_id, grade, quality, ease_factor_before/after,
  interval_before/after, reviewed_at)`

## Cost & resource controls

| Control | Where | Purpose |
|---|---|---|
| Rate limiting | `app/core/ratelimit.py`, per-IP sliding window | cap LLM/STT endpoint frequency |
| Spend budget | `app/core/budget.py`, rolling 24 h | cap paid calls per day (`LLM_DAILY_LIMIT`, `DEEPGRAM_DAILY_LIMIT`) |
| TTL cache | `app/core/cache.py` | news/podcast (10 min) and dictionary (24 h) with in-flight coalescing |
| Retry + jitter | `llm.py` / `deepgram.py` | retry 5xx/429/transport with exponential backoff + jitter |

All LLM-generative drill/coach/writing/speaking/plan endpoints are wrapped with
the per-IP `rate_limited` dependency **and** the 24-hour spend budget, so a
misbehaving kiosk cannot blow past the daily cap.

## Speech-to-text providers

Pre-recorded transcription (`POST /api/radio/transcribe`, used by the podcast
Transcript feature) is pluggable via `STT_PROVIDER`:

- `deepgram` (default) — `app/services/deepgram.py`, paid, cloud, budgeted.
- `whisper` — `app/services/whisper.py`, a local whisper.cpp server
  (`/inference` endpoint), free and offline.

Both implement the same `DeepgramProvider` protocol, so `RadioService` and the
HTTP layer are unchanged. The live radio teleprompter (`/ws/radio`) still uses
Deepgram's streaming endpoint and requires a `DEEPGRAM_API_KEY`.

## Error-handling strategy

Domain errors map to HTTP status codes via global handlers in `app/main.py`:

| Exception | Status |
|---|---|
| `LLMNotConfiguredError` / `DeepgramNotConfiguredError` | 503 |
| `LLMBudgetExceeded` / `DeepgramBudgetExceeded` | 429 |
| `LLMError` / `DeepgramError` (upstream) | 502 |
| Pydantic validation error | 422 |
| `SrsError` (not found) | 404 |

Content services (`news.py`, `podcast.py`) catch LLM failures and degrade rather than
propagate, so the dashboard always renders something.

## Key algorithms

- **SM-2** (`app/services/srs_engine.py`): pure functions, Ease Factor floored at 1.3,
  `q<3` resets repetitions without changing EF, `I(1)=1`, `I(2)=6`, `I(n)=I(n-1)·EF`.
  UI grades map `1→Again(0), 2→Hard(3), 3→Good(4), 4→Easy(5)`.
- **Discourse connectors** (`app/services/connectors.py`): case-insensitive,
  word-boundary matching; the client mirrors it (`static/js/lib/connectors.js`).
- **Live STT** (`app/services/deepgram_live.py`): a WebSocket session that relays
  browser-captured 16-bit PCM to Deepgram's live endpoint and parses `Results` messages.
