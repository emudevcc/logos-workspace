# Logos Workspace

Multi-cockpit study dashboard: **English · Português · Bíblia** in one always-on
workspace. Built to run headless on a **Raspberry Pi 3B** (1 GB RAM) in Chromium
kiosk mode or as a **macOS LaunchAgent** on `https://localhost`.

- **Backend:** FastAPI (async), WebSockets, aiosqlite (WAL), external LLM/STT only — no local model.
- **Frontend:** Vanilla ES modules + Tailwind/DaisyUI, bundled with Vite via
  `npm run build`; still runs zero-build when no bundle exists.
- **Process model:** a single async uvicorn worker; one shared `httpx.AsyncClient`,
  one aiosqlite connection, and one WebSocket registry live on `app.state` for the
  whole process lifetime (no per-request churn on a small machine).

## Cockpits

A **cockpit** is one study domain: sidebar sections, SRS decks, and header stats
are scoped per cockpit (persisted selection, `?cockpit=en|pt|bible`).

| Cockpit | Content |
|---|---|
| **English** | The original English immersion dashboard: Today / Practice / Speak / Write — word & idiom of the day, tech & business news, podcast digest, SRS flashcards, grammar & pronunciation drills, PREP drill, voice roleplay, speech metrics, radio + teleprompter, writing coach, register swap, weekly plan. |
| **Português** (PT-BR) | Immersion for a native Spanish speaker at intermediate/advanced level, with Spanish scaffolding (`nota_es`/`l1_hint`) on false friends, grammar traps, and pronunciation. Palavra do dia, Notícias do Brasil, flashcards PT-BR (vocabulário essencial + falsos cognatos), gramática (regra do dia + coach LLM), pronúncia (pares mínimos + pegadinhas), frases para repetir. |
| **Bíblia** | Pericope exegesis (5–15 verses): six-section study reports — literary framework, historical-grammatical context, lexical exegesis with consensus notes, redemptive-theological context, core principle, practical application — grounded on deterministic 66-book profiles, with guardrails (literal-grammatical priority, no speculative allegorization, evangelical orthodoxy, no uncited claims). Saved studies + 66-book registry browser. |

Bible text is fetched from **API.Bible** (api.scripture.api.bible) and cached in
SQLite. The passage text can be read in **Español · English · Português** (defaults:
NTV, NIV, NVT — per-language labels are configurable). Study output stays in
Spanish, the reader's native base. RVR60 is not in the API.Bible Spanish catalog.

## Documentation

- [Architecture](docs/ARCHITECTURE.md) — process/resource model, persistence, migrations, algorithms
- [API Reference](docs/API.md) — all endpoints, schemas, and WebSocket protocols
- [Frontend](docs/FRONTEND.md) — cockpit shell, module layout, event flow, testing
- [Deployment & Operations](docs/DEPLOYMENT.md) — config, LaunchAgent, deploy.sh, security

## Layout

```
app/
  main.py                  app factory, lifespan, DI, exception handlers, static mount
  core/db.py               aiosqlite (WAL) + versioned migrations
  api/                     routers: content, learning, srs, prep, assist, plan,
                           websocket, radio_ws, routes_pt (Português), routes_bible
  schemas/                 Pydantic models incl. pt.py and bible.py (study schema)
  services/
    srs.py srs_engine.py srs_seed.py pt_seed.py   SRS (SM-2) + per-cockpit seeding
    llm.py deepgram*.py whisper.py                external inference clients
    news.py podcast.py rss.py radio.py dictionary.py   English content pipelines
    word_of_day.py grammar_rules.py grammar_drill.py minimal_pairs.py irregular_verbs.py
    pt_content.py pt_generators.py pt_news.py     Português cockpit (curated + LLM)
    bible_books.py bible_parser.py bible_provider.py bible_studies.py   Bíblia cockpit
static/
  css/main.css css/cockpit.css
  js/main.js               boot: cockpit switcher + lazy per-cockpit module mount
  js/lib/                  api, bus, dom, cockpit (identity), bible_render, …
  js/components/           one module per card (word_of_day, news, srs_deck, pt_*,
                           bible_study, bible_history, bible_books, …)
templates/index.html       shell: cockpit switcher + one nav/panel set per cockpit
tests/                     pytest (backend) + node:test (frontend)
```

## API

| Method | Path | Notes |
|---|---|---|
| GET | `/healthz` | liveness + `llm_configured`/`bible_configured`/`stt_provider`/… |
| WS  | `/ws`, `/ws/radio` | broadcast/heartbeat bus; live STT relay |
| GET | `/api/word-of-day`, `/entries`, `/random` | English word of the day |
| GET | `/api/news`, `/api/podcast-digest`, `/api/dictionary/lookup?word=` | English content |
| GET | `/api/srs/decks?cockpit=`, `/stats?cockpit=`, `/decks/{id}/new`, `/due` | SRS per cockpit (default `en`) |
| POST | `/api/srs/cards?cockpit=`, `/api/srs/review` | add card (supports `l1_hint`) / grade |
| GET | `/api/prep/scenario`, `/api/grammar/*`, `/api/pronunciation/*`, `/api/speech/*`, `/api/radio/*` | English drills & coaches (LLM where noted) |
| POST | `/api/prep/evaluate`, `/api/declutter`, `/api/voice/turn`, `/api/quiz`, `/api/register/rewrite`, `/api/writing/correct`, `/api/plan/weekly`, `/api/grammar/coach` | LLM endpoints |
| GET | `/api/pt/word-of-day(/-random)`, `/api/pt/news` | Português |
| GET | `/api/pt/grammar/rules`, `/rule-of-day`, `/rule-random`, `/pronunciation/minimal-pairs`, `/pitfalls`, `/practice/sentence` | Português |
| POST | `/api/pt/grammar/coach` | Português LLM coach |
| GET | `/api/bible/books`, `/api/bible/passage?reference=` | Bíblia registry + RVR text |
| POST | `/api/bible/study` | six-section exegesis (LLM), saved |
| GET/DELETE | `/api/bible/studies[/{id}]` | study history |

LLM/Bible/Deepgram "not configured" → `503`; upstream failure → `502`; bad
reference/input → `422`.

## Run locally (macOS)

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp deploy/env.example .env           # then add LLM_API_KEY (+ BIBLE_API_KEY for Bíblia)
.venv/bin/python -m app              # https://localhost:8000 (TLS when configured)
```

Bundle the frontend (optional; served from source when absent):

```bash
npm ci
npm run build                        # outputs static/dist/
npm run dev                          # HMR dev server on :5173 (proxies /api and /ws)
```

Run as a **macOS LaunchAgent** on `https://localhost:8090` (without touching the
legacy English agent on :8000):

```bash
PORT=8090 HOST=127.0.0.1 ./deploy/macos/install-logos-agent.sh
open https://localhost:8090
```

## Configuration

Create a `.env` (gitignored) next to the app. Values are read once at startup.

| Env var | Default | Notes |
|---|---|---|
| `COCKPIT_DB` | `data/cockpit.db` | SQLite location. |
| `LLM_API_KEY` | *(empty)* | Groq key; enables all generative features. |
| `LLM_BASE_URL` | `https://api.groq.com/openai/v1` | OpenAI-compatible endpoint. |
| `LLM_MODEL` | `qwen/qwen3.8-27b` | Any JSON-mode-capable model on your Groq account. |
| `LLM_DAILY_LIMIT` | `1000` | Max LLM calls per 24 h (0 = unlimited). |
| `DEEPGRAM_API_KEY` | *(empty)* | Enables transcription/roleplay audio. |
| `STT_PROVIDER` | `deepgram` | Pre-recorded STT backend: `deepgram` or `whisper` (local). |
| `WHISPER_BASE_URL` | `http://localhost:8080` | whisper.cpp server base URL. |
| `BIBLE_API_KEY` | *(empty)* | API.Bible key; enables the Bíblia cockpit text. |
| `BIBLE_API_BASE_URL` | `https://api.scripture.api.bible/v1` | API.Bible base URL. |
| `BIBLE_DEFAULT_TRANSLATION` | `NTV` | Spanish text default (Nueva Traducción Viviente). |
| `BIBLE_ENGLISH_TRANSLATION` | `NIV` | English text default (New International Version). |
| `BIBLE_PORTUGUESE_TRANSLATION` | `NVT` | Portuguese text default (Nova Versão Transformadora). |
| `BIBLE_API_CACHE_TTL_SECONDS` | `604800` | Passage cache TTL (7 days). |
| `RATE_LIMIT_PER_MINUTE` | `30` | Per-IP rate limit on LLM/Bible/STT endpoints. |
| `HOST` / `PORT` | `127.0.0.1` / `8000` | Bind address/port. |
| `TLS_CERTFILE` / `TLS_KEYFILE` | *(empty)* | Enable HTTPS (macOS `deploy/macos/certs.sh`). |

News/podcast/radio feeds and curated PT-BR and book-profile data are code
constants in `app/services/*` — edit and redeploy to change them.

## Tests

```bash
.venv/bin/python -m pytest -q    # backend (237)
npm test                          # frontend pure logic (64)
```

## Security

The app has **no application-level authentication** and binds to **127.0.0.1**
by default. Remote access is via SSH tunnel or a reverse proxy (Caddy with basic
auth) — never expose the app directly to the public internet. Spending is capped
by rate limiting and daily budgets; API.Bible passages are cached locally.

## Deploy

- **macOS:** LaunchAgent (`deploy/macos/install-logos-agent.sh`, port 8090) or
  run `python -m app` directly; HTTPS via `deploy/macos/certs.sh`.
- **Raspberry Pi:** `deploy.sh` is test-gated and rsyncs the tree (excluding
  `.venv/`, `data/`, `tests/`, secrets) to the Pi, installs/updates the systemd
  unit (`deploy/english-cockpit.service`), and waits for `/healthz`.

This project started as [English Cockpit OS](https://github.com/emudevcc/English-Cockpit-OS)
(the English cockpit above); the English product remains a separate public repo.
