# Logos Workspace

Modular English immersion + rapid-practice dashboard for a **Raspberry Pi 3B**
(1 GB RAM) running 24/7 on a secondary display in Chromium Kiosk mode.

- **Backend:** FastAPI (async), WebSockets, aiosqlite (WAL), external LLM/STT only — no local model.
- **Frontend:** Vanilla HTML5 + CSS Grid + ES Modules (no framework) — bundled and
  minified with Vite via `npm run build`; still runs zero-build when no bundle exists.
- **Process model:** a single async uvicorn worker; one shared `httpx.AsyncClient`,
  one aiosqlite connection, and one WebSocket registry live on `app.state` for the
  whole process lifetime (no per-request churn on a 1 GB budget).

## Documentation

- [Architecture](docs/ARCHITECTURE.md) — process/resource model, persistence, cost controls, algorithms
- [API Reference](docs/API.md) — all endpoints, schemas, and WebSocket protocols
- [Frontend](docs/FRONTEND.md) — module layout, event flow, feature components, testing
- [Deployment & Operations](docs/DEPLOYMENT.md) — config, deploy.sh, systemd, kiosk, security

## Layout

```
app/
  __main__.py              `python -m app` entrypoint (binds 127.0.0.1)
  main.py                  app factory, lifespan, DI, exception handlers, static mount
  api/websocket.py         /ws endpoint (ping/pong heartbeat)
  api/routes_radio_ws.py   /ws/radio live STT relay (browser audio -> Deepgram)
  api/routes_content.py    word-of-day, news, podcast digest, dictionary
  api/routes_learning.py   verbs, minimal pairs, pitfalls, grammar drills + coach
  api/routes_srs.py        SRS decks / due cards / review
  api/routes_prep.py       PREP scenario + evaluate
  api/routes_assist.py     declutter, writing-correct, voice, radio, speech, monologue
  api/routes_plan.py       weekly study plan
  api/deps.py              shared dependencies (rate limiting)
  core/config.py           typed settings (pydantic-settings)
  core/db.py               aiosqlite (WAL) + explicit write transactions
  core/timeutil.py         canonical UTC timestamp helpers
  core/cache.py            async TTL cache
  core/ratelimit.py        sliding-window rate limiter
  core/budget.py           daily spend budget
  core/ws_manager.py       connection registry + broadcaster + heartbeat
  schemas/                 strict Pydantic request/response models
  services/
    srs_engine.py          pure SM-2 (EF floor 1.3)
    srs.py, srs_seed.py    SRS persistence + seed deck
    llm.py                 Groq client with retry + JSON mode + budget
    deepgram.py            Deepgram pre-recorded STT client
    deepgram_live.py       Deepgram live (streaming) STT session
    whisper.py             local whisper.cpp STT client (when STT_PROVIDER=whisper)
    rss.py                 feed fetch/parse (offloaded to a thread)
    news.py, podcast.py    content pipelines (cached, graceful degrade)
    prep.py, declutter.py, voice.py, radio.py, connectors.py
    dictionary.py          click-to-translate lookup (cached)
    quiz.py, register.py   comprehension quiz + register rewrite
    irregular_verbs.py     curated irregular verbs (deterministic, no LLM)
    minimal_pairs.py       curated minimal pairs + pitfalls (deterministic, no LLM)
    grammar_rules.py       curated Rule-of-the-Day (deterministic, no LLM)
    grammar_drill.py       LLM phrasal/collocation/use-of-English/word-form drills + coach
    writing.py             LLM grammar/usage correction
    monologue.py           curated monologue topics + LLM feedback
    plan.py                LLM weekly study plan
static/
  css/cockpit.css          dark-mode CSS Grid, accessible
  js/main.js               boots WS + event bus + modules
  js/ws_client.js          auto-reconnecting WebSocket client (1s→15s backoff)
  js/lib/*.js              pure logic: timer, speech, srs, text, connectors, highlight, shadow, drill, word_extract, audio, pronounce, api, bus, backoff, dom
  js/components/*.js       one module per feature (word_of_day, news, podcast, radio, srs_deck, prep_drill, grammar, declutter, voice, speech_coach, dictionary, shadowing, register, weekly_plan, stats)
templates/index.html       kiosk dashboard shell (13 cards)
deploy/Caddyfile           optional LAN exposure with basic auth
tests/backend              pytest (175 tests)
tests/frontend             node:test (55 tests)
```

## API

| Method | Path | Notes |
|---|---|---|
| GET | `/healthz` | liveness + `llm_configured`/`stt_provider`/`whisper_configured` |
| GET | `/healthz/external` | live Groq/Deepgram reachability probe |
| WS  | `/ws` | heartbeat (`ping`/`pong`) + broadcast bus |
| WS  | `/ws/radio` | live STT relay (browser PCM upload → Deepgram) |
| GET | `/api/word-of-day` | deterministic daily rotation (`?date=` optional) |
| GET | `/api/word-of-day/entries` | curated archive list |
| GET | `/api/news` | 3 headlines + vocab (LLM vocab when key set) |
| GET | `/api/podcast-digest` | brief + key terms + episode audio |
| GET | `/api/dictionary/lookup?word=` | click-to-translate (cached 24 h) |
| GET | `/api/srs/decks` | decks with due counts |
| GET | `/api/srs/decks/{id}/due` | review cards due (seen before) |
| GET | `/api/srs/decks/{id}/new` | unseen cards (introduce up to `new_cards_per_day`) |
| POST | `/api/srs/cards` | add a card |
| POST | `/api/srs/review` | grade a card (`{card_id, grade: 1..4}`) |
| GET | `/api/srs/stats` | due/new/total/reviews-today/streak/daily-goal |
| GET | `/api/srs/export` | JSON backup of decks + cards |
| GET | `/api/prep/scenario` | random workplace scenario |
| POST | `/api/prep/evaluate` | PREP feedback + BLUF rewrite |
| POST | `/api/declutter` | word reduction + verb upgrades + tone |
| POST | `/api/voice/turn` | roleplay partner turn |
| POST | `/api/quiz` | comprehension MCQ from text |
| POST | `/api/register/rewrite` | rewrite a sentence in a target register |
| GET | `/api/radio/stations` | live stream URLs |
| POST | `/api/radio/transcribe` | Deepgram transcript + connector highlights |
| GET | `/api/speech/connectors` | discourse-connector list |
| GET | `/api/grammar/irregular-verbs` | curated irregular-verb list (deterministic) |
| GET | `/api/grammar/drill?kind=` | LLM cloze MCQ (`phrasal_verb`/`collocation`/`use_of_english`) |
| GET | `/api/grammar/word-forms` | LLM gap-fill (correct derived form) |
| GET | `/api/grammar/rule-of-day` | deterministic daily grammar rule (`?date=` optional) |
| POST | `/api/grammar/coach` | free-form grammar question → LLM answer |
| GET | `/api/pronunciation/minimal-pairs` | curated minimal pairs (deterministic) |
| GET | `/api/pronunciation/pitfalls` | curated Spanish-speaker pitfalls (deterministic) |
| POST | `/api/writing/correct` | grammar/usage correction + per-error explanations |
| GET | `/api/speech/topics` | curated monologue topics |
| POST | `/api/speech/monologue/evaluate` | LLM speaking feedback (4 scores + model answer) |
| POST | `/api/plan/weekly` | LLM seven-day study plan |

LLM/Deepgram "not configured" → `503`; upstream failure → `502`; bad input → `422`.

## Run locally

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m app
```

Optionally bundle/minify the frontend (served automatically when present):

```bash
npm install
npm run build      # outputs static/dist/; `npm run dev` starts a HMR dev server
```

Point a browser at `http://localhost:8000` (or `https://localhost:8000` when TLS is
configured). Remote access via SSH tunnel:

```bash
ssh -L 8000:localhost:8000 pi@host
```

## Configuration

Create a `.env` (gitignored) next to the app. Values are read once at startup.

| Env var | Default | Notes |
|---|---|---|
| `COCKPIT_DB` | `data/cockpit.db` | SQLite location. |
| `LLM_API_KEY` | *(empty)* | Groq key; enables all generative features (drills, coach, writing, monologue, plan, etc.). |
| `LLM_BASE_URL` | `https://api.groq.com/openai/v1` | OpenAI-compatible endpoint. |
| `LLM_MODEL` | `qwen/qwen3.8-27b` | Any JSON-mode-capable model on your Groq account. |
| `LLM_TIMEOUT_SECONDS` | `60` | Per-request LLM timeout. |
| `LLM_MAX_RETRIES` | `2` | Bounded retries on 5xx/429/transport. |
| `DEEPGRAM_API_KEY` | *(empty)* | Enables `/api/radio/transcribe`. |
| `DEEPGRAM_MODEL` | `nova-2` | Deepgram model. |
| `DEEPGRAM_TIMEOUT_SECONDS` | `300` | Transcription timeout (long audio). |
| `DEEPGRAM_MAX_RETRIES` | `2` | Retries on 5xx/429/transport. |
| `DEEPGRAM_ALLOWED_HOSTS` | `[]` | JSON list; if set, restrict `audio_url` hosts. |
| `CORS_ORIGINS` | `[]` | JSON list; empty = same-origin only (kiosk default). |
| `CONTENT_CACHE_TTL_SECONDS` | `600` | News/podcast cache TTL. |
| `RATE_LIMIT_PER_MINUTE` | `30` | Per-IP rate limit on LLM/STT endpoints. |
| `LLM_DAILY_LIMIT` | `1000` | Max LLM calls per 24h (0 = unlimited). |
| `DEEPGRAM_DAILY_LIMIT` | `200` | Max Deepgram calls per 24h (0 = unlimited). |
| `STT_PROVIDER` | `deepgram` | Pre-recorded STT backend: `deepgram` or `whisper` (local). |
| `WHISPER_BASE_URL` | `http://localhost:8080` | whisper.cpp server base URL (used when `STT_PROVIDER=whisper`). |
| `WHISPER_TIMEOUT_SECONDS` | `300` | Transcription timeout. |
| `WHISPER_MAX_RETRIES` | `2` | Retries on 5xx/transport. |
| `TLS_CERTFILE` | *(empty)* | TLS cert path (from `deploy/macos/certs.sh`); enables HTTPS when set with `TLS_KEYFILE`. |
| `TLS_KEYFILE` | *(empty)* | TLS private-key path. |
| `WS_MAX_CONNECTIONS` | `100` | WebSocket connection cap. |
| `NEW_CARDS_PER_DAY` | `10` | New SRS cards introduced per session. |
| `DAILY_REVIEW_GOAL` | `20` | Daily review goal for the header ring. |

Feed URLs are defined as constants in `app/services/news.py`, `podcast.py`, and
`radio.py` — edit and redeploy to change them.

## Tests

```bash
.venv/bin/python -m pytest -q    # backend (175)
npm test                          # frontend pure logic (55)
```

## Security

The app has **no application-level authentication** and binds to **127.0.0.1**
by default, so only the local kiosk (or an SSH tunnel) can reach it. Remote
access is intended via SSH:

```bash
ssh -L 8000:localhost:8000 pi@host   # then browse http://localhost:8000
```

For LAN-wide browsing, use `deploy/Caddyfile` (Caddy with basic auth in front of
`127.0.0.1:8000`). Spending is capped by `RATE_LIMIT_PER_MINUTE`, `LLM_DAILY_LIMIT`,
and `DEEPGRAM_DAILY_LIMIT`. Do not expose the app directly to the public internet.

## Deploy to the Pi

One-time setup on the Pi: create the app dir, add secrets, and install the unit.

```bash
# on the Pi (once)
mkdir -p /home/pi/english-cockpit
cp deploy/env.example /home/pi/english-cockpit/.env   # then edit the keys
sudo cp deploy/english-cockpit.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable english-cockpit
```

Then deploy from your Mac:

```bash
PI_HOST=raspberrypi.local INSTALL_DEPS=1 INSTALL_UNIT=1 ./deploy.sh   # first time
./deploy.sh                                                          # afterwards
```

`deploy.sh` refuses to proceed unless both test gates pass, then rsyncs the tree
(excluding `.venv/`, `data/`, `tests/`, and secrets), restarts the unit, and
waits up to 15s for `/healthz`. `INSTALL_DEPS=1` builds the venv on the Pi;
`INSTALL_UNIT=1` installs/enables the systemd unit.

Start the kiosk on the Pi (or add it to the Pi's autostart):

```bash
deploy/kiosk.sh
```

## Kiosk note (RAM)

`deploy/kiosk.sh` launches Chromium in kiosk mode with memory-friendly flags
(`--kiosk --noerrdialogs --disable-gpu --no-sandbox`). Override the browser
with `BROWSER=chromium-browser` if needed.
