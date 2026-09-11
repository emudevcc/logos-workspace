# Deployment & Operations

Target: **macOS (Apple Silicon)**, Python 3.11+. The original Raspberry Pi 3B
target is still supported via `deploy.sh` / systemd.
Dev machine: macOS with Python 3.11+ and Node.js (for frontend tests).

## Local development

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m app        # binds 127.0.0.1:8000
```

Remote access from the dev machine via SSH tunnel:

```bash
ssh -L 8000:localhost:8000 pi@<pi-host>
```

## Configuration

Secrets and tuning live in a `.env` file (gitignored) in the app directory, read once
at startup. Copy `deploy/env.example` and fill in the keys.

| Env var | Default | Purpose |
|---|---|---|
| `COCKPIT_DB` | `data/cockpit.db` | SQLite location |
| `LOG_PATH` | `data/logos.log` | rotating app log file (see below) |
| `LOG_MAX_BYTES` | `5242880` | rotate past this size; `0` disables file logging |
| `LOG_BACKUP_COUNT` | `3` | rotated files to retain |
| `LOG_LEVEL` | `INFO` | root log level (unknown values fall back to `INFO`) |
| `LLM_API_KEY` | *(empty)* | Groq key; enables LLM features |
| `LLM_BASE_URL` | `https://api.groq.com/openai/v1` | OpenAI-compatible endpoint |
| `LLM_MODEL` | `qwen/qwen3.8-27b` | model on your Groq account |
| `LLM_TIMEOUT_SECONDS` | `60` | per-request LLM timeout |
| `LLM_MAX_RETRIES` | `3` | retries on 5xx/429/transport |
| `LLM_DAILY_LIMIT` | `1000` | max LLM calls / 24 h (0 = unlimited) |
| `DEEPGRAM_API_KEY` | *(empty)* | enables transcription |
| `DEEPGRAM_MODEL` | `nova-2` | Deepgram model |
| `DEEPGRAM_TIMEOUT_SECONDS` | `300` | transcription timeout |
| `DEEPGRAM_MAX_RETRIES` | `2` | retries on 5xx/429/transport |
| `DEEPGRAM_ALLOWED_HOSTS` | `[]` | JSON list restricting `audio_url` hosts |
| `DEEPGRAM_DAILY_LIMIT` | `200` | max Deepgram calls / 24 h |
| `STT_PROVIDER` | `deepgram` | pre-recorded STT backend: `deepgram` or `whisper` |
| `WHISPER_BASE_URL` | `http://localhost:8080` | whisper.cpp server base URL |
| `WHISPER_TIMEOUT_SECONDS` | `300` | transcription timeout |
| `WHISPER_MAX_RETRIES` | `2` | retries on 5xx/transport |
| `BIBLE_API_KEY` | *(empty)* | API.Bible key; enables the Bíblia cockpit |
| `BIBLE_API_BASE_URL` | `https://api.scripture.api.bible/v1` | API.Bible base URL |
| `BIBLE_DEFAULT_TRANSLATION` | `NTV` | Spanish text default (Nueva Traducción Viviente) |
| `BIBLE_ENGLISH_TRANSLATION` | `NIV` | English text default (New International Version) |
| `BIBLE_PORTUGUESE_TRANSLATION` | `NVT` | Portuguese text default (Nova Versão Transformadora) |
| `BIBLE_API_CACHE_TTL_SECONDS` | `604800` | passage cache TTL (7 days) |
| `RATE_LIMIT_PER_MINUTE` | `30` | per-IP limit on LLM/STT endpoints |
| `CONTENT_CACHE_TTL_SECONDS` | `600` | news/podcast cache TTL |
| `DICTIONARY_CACHE_TTL_SECONDS` | `86400` | dictionary cache TTL |
| `CORS_ORIGINS` | `[]` | JSON list; empty = same-origin only |
| `WS_MAX_CONNECTIONS` | `100` | WebSocket cap |
| `NEW_CARDS_PER_DAY` | `10` | new SRS cards introduced per session |
| `DAILY_REVIEW_GOAL` | `20` | daily review goal for the header ring |
| `HOST` / `PORT` | `127.0.0.1` / `8000` | bind address/port |

Feed URLs (news/podcast/radio stations) are code constants in
`app/services/{news,podcast,radio}.py`.

### Worst-case latency of a Bíblia study

`POST /api/bible/study` combines two retry layers, so its worst case is
derived from the defaults above rather than enforced by a timeout of its own:

- up to **2 business attempts** (the service retries once when the model
  returns unusable or schema-invalid JSON), each of which is
- up to **`LLM_MAX_RETRIES + 1` = 4 network attempts**, each able to consume
- up to **`LLM_TIMEOUT_SECONDS` = 60 s**, plus
- up to one **15 s `Retry-After` wait** per network attempt that returns 429.

A `Retry-After` wait is *not* compounded with the jittered backoff for the
same retried attempt, so the backoff ceiling (≤ 4 s) is skipped on those
transitions. The theoretical ceiling is therefore
`2 × (4 × 60 s + 4 × 15 s)` ≈ 10 minutes, reached only when every attempt
times out or is rate-limited; a normal transient failure recovers well inside
the first timed-out call's budget. There is deliberately no enforced
wall-clock deadline on this path — see `plans/` notes on why cancelling an
in-flight request on the process-wide shared `httpx.AsyncClient` was rejected.

## Local Whisper (STT)

Run speech-to-text offline with a local whisper.cpp server (free, no Deepgram key):

```bash
git clone https://github.com/ggml-org/whisper.cpp
cd whisper.cpp                               # run every step below from INSIDE this folder
sh ./models/download-ggml-model.sh small     # base | small | medium (size vs accuracy)
cmake -B build                               # Metal is auto-enabled on Apple Silicon
cmake --build build -j
./build/bin/whisper-server -m models/ggml-small.bin --host 127.0.0.1 --port 8080
```

Then set in `.env`:

```
STT_PROVIDER=whisper
WHISPER_BASE_URL=http://localhost:8080
```

The app downloads the audio and POSTs it to the server's `/inference` endpoint,
so pre-recorded transcription (the podcast **Transcript** button and
`/api/radio/transcribe`) works with no Deepgram key.
The live radio teleprompter (`/ws/radio`) still uses Deepgram and needs
`DEEPGRAM_API_KEY`. See the whisper.cpp README for the latest build flags.

## HTTPS (local, macOS)

Microphone and clipboard APIs require a secure context, which only works over
HTTPS when served from anything other than `localhost`. Generate a locally-trusted
certificate with [mkcert](https://github.com/FiloSottile/mkcert):

```bash
brew install mkcert
./deploy/macos/certs.sh        # generates deploy/certs/localhost.{pem,key}
```

Then set in `.env`:

```
HOST=0.0.0.0
TLS_CERTFILE=deploy/certs/localhost.pem
TLS_KEYFILE=deploy/certs/localhost-key.pem
```

Restart and open `https://localhost:8000` (or `https://<lan-ip>:8000` from another
device). `certs.sh` runs `mkcert -install` once to trust the local CA (asks for your
password).

## macOS autostart

Install a LaunchAgent (starts on login, restarts on crash):

```bash
./deploy/macos/install-agent.sh     # legacy label com.englishcockpit.os (port 8000)
./deploy/macos/install-logos-agent.sh  # Logos Workspace, com.logosworkspace.os, port 8090
```

The Logos LaunchAgent binds `127.0.0.1:8090` via plist `EnvironmentVariables`
and never touches the legacy English agent on :8000. Point a browser at
`https://localhost:8090`.

Open the dashboard in a standalone app-mode Chrome window (no tabs/address bar):

```bash
./deploy/macos/launch.sh        # COCKPIT_URL=https://localhost:8000 by default
```

## One-time Pi setup

```bash
mkdir -p /home/pi/english-cockpit
cp deploy/env.example /home/pi/english-cockpit/.env   # edit keys
sudo cp deploy/english-cockpit.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable english-cockpit
```

## Deploying (`deploy.sh`)

Run from the dev machine (repo root). It is **test-gated** — it refuses to deploy
unless backend and frontend tests pass.

```bash
PI_HOST=raspberrypi.local INSTALL_DEPS=1 INSTALL_UNIT=1 ./deploy.sh   # first time
./deploy.sh                                                          # afterwards
```

Flags / env:

| Var | Default | Purpose |
|---|---|---|
| `PI_HOST` | `raspberrypi.local` | Pi hostname/IP |
| `PI_USER` | `pi` | SSH user |
| `APP_DIR` | `/home/pi/english-cockpit` | install dir |
| `UNIT_NAME` | `english-cockpit` | systemd unit name |
| `PORT` | `8000` | health-check port |
| `INSTALL_DEPS=1` | off | build the venv + install requirements on the Pi |
| `INSTALL_UNIT=1` | off | install/enable the systemd unit |

Flow: `pytest` → `npm test` → rsync (excluding `.venv/`, `data/`, `tests/`, `.env`,
caches) → (optional deps/unit install) → `systemctl restart` → wait up to 15 s for
`/healthz`.

## systemd unit (`deploy/english-cockpit.service`)

Runs `python -m app` (binds 127.0.0.1), `Restart=always`, `After=network-online.target`.
The `.env` is read by pydantic-settings from the working directory.

## Kiosk (`deploy/kiosk.sh`)

Launches Chromium with memory-friendly flags (`--kiosk --noerrdialogs --disable-gpu
--no-sandbox`). Override `BROWSER` (e.g. `chromium-browser`) if needed. Add it to the
Pi's autostart for a 24/7 dashboard.

## Optional LAN exposure (`deploy/Caddyfile`)

The app binds to localhost by default. If you need LAN-wide browsing (without an SSH
tunnel), front it with Caddy + basic auth:

```bash
caddy hash-password --plaintext 'your-password'
COCKPIT_BASIC_AUTH_HASH='$2a$14$…' caddy run --config deploy/Caddyfile
```

Caddy listens on `:8080` and proxies to `127.0.0.1:8000`.

## Security model

- **No application-level auth.** The app is intended for a trusted LAN and binds to
  `127.0.0.1` by default; remote access is via authenticated SSH tunnel.
- CORS is same-origin by default (`CORS_ORIGINS=[]`).
- Spending is capped by rate limiting and daily budgets; the dictionary/news/podcast
  caches reduce redundant paid calls.
- Do **not** expose the app directly to the public internet. Use Caddy/reverse proxy
  or network isolation for anything beyond a LAN.

## Operations

- **Health**: `curl https://localhost:8090/healthz` (Logos LaunchAgent) or `:8000` (legacy English agent).
- **Logs**: two destinations on both targets, by design:
  - `data/logos.log` — the app's own rotating log (see below). This is where
    `app.*` records go, and it is size-capped.
  - The process stream: `tail -f data/logos-agent.log` on the macOS LaunchAgent
    (its `StandardOutPath`/`StandardErrorPath` redirect), or
    `journalctl -u english-cockpit -f` on the Pi/systemd target (journald does
    its own retention). Uvicorn's startup lines land here.
- **Log rotation**: `app/core/logging_setup.py` attaches a
  `RotatingFileHandler` to `LOG_PATH` (default `data/logos.log`), rotating at
  `LOG_MAX_BYTES` and keeping `LOG_BACKUP_COUNT` archives. It is installed by
  the `python -m app` entrypoint, so it applies to both deployment targets and
  needs no root.
  - Rotation deliberately targets a **separate** file from the LaunchAgent's
    `data/logos-agent.log`. The running process holds that file open for
    append, and renaming its inode would not make the process follow it — the
    renamed archive would keep growing while the fresh file stayed empty. A
    handler that owns its own file rotates correctly with no restart.
  - Set `LOG_MAX_BYTES=0` to disable file logging entirely and rely on the
    process stream as before.
  - Already deployed and just want the old, oversized file gone? Truncating
    `data/logos-agent.log` while the agent runs is safe (`: > data/logos-agent.log`)
    — the open descriptor keeps appending from offset 0.
- **Database**: `data/cockpit.db` (WAL); it is excluded from deploys so SRS progress
  survives updates.
- **Feed drift**: BBC/The Guardian/NPR feed URLs are the most likely thing to break over
  time — they're constants in the service modules (edit + redeploy).

### Diagnosing a failed Bíblia study

The app attaches a size-capped `RotatingFileHandler` to `data/logos.log` (see
Operations above), and `app.*` records also propagate to the process stream —
`data/logos-agent.log` on the macOS LaunchAgent, or `journalctl -u
english-cockpit -f` on the Pi/systemd path. The Bíblia study path emits:

| Line | Level | Meaning |
|---|---|---|
| `bible study retry reason=... ref=...` | WARNING | The first attempt failed and a corrective retry is about to run. `reason` is `LLMJsonValidationError` (unusable JSON) or `LLMSchemaMismatchError` (valid JSON, wrong shape — the line also names the failing field paths). |
| `bible study failed reason=... ref=...` | ERROR | Both attempts were exhausted; the route returns a 502 with a friendly Spanish detail. |
| `llm retry attempt=N/M sleep=...` | WARNING | A network-level retry inside one `complete_json` call. `sleep` is `backoff`, `retry-after`, or `none` (the last only for an attempt that follows an honored `Retry-After`). |
| `llm transport error attempt=N/M error=...` | WARNING | `httpx.TransportError` — connection/TLS/DNS rather than an HTTP status. |
| `llm upstream error attempt=N/M status=...` | WARNING | 429 or 5xx from the provider. |
| `llm json-failure fallback detection fired` | WARNING | The provider's 400 had no structured `error.code`, so the substring heuristic classified it as a JSON failure. If this fires, `LLM_BASE_URL` points somewhere whose error shape differs from Groq's. |
| `llm retries exhausted attempts=N last_error=...` | ERROR | Every network attempt failed; a `LLMError` is about to be raised. |

A transient failure that recovers logs one WARNING and no ERROR; a totally
failed study logs the ERROR pair. Logged text is truncated via the shared
`_truncate()` helper — no API key, `Authorization` header, full passage text,
or full model response body ever reaches the log.
