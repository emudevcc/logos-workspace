# API Reference

Base path: all routes are under `/api` unless noted. Content is JSON; requests
and responses are validated with Pydantic. Error bodies are `{"detail": "..."}`.

## Status codes

| Code | Meaning |
|---|---|
| 200 / 201 | success (201 for created SRS cards) |
| 404 | card/deck not found |
| 422 | validation error (`extra="forbid"` on request models) |
| 429 | rate limit or daily spend budget exceeded |
| 502 | external LLM/Deepgram upstream failure |
| 503 | LLM/Deepgram not configured (missing key) |

## System

### `GET /healthz`
Liveness probe + config flags:
`{"status":"ok","app":"English Cockpit OS","llm_configured":true,"stt_provider":"deepgram","deepgram_configured":true,"whisper_configured":false}`

### `GET /healthz/external`
Live (free) reachability probe of Groq and Deepgram:
`{"llm":"ok","deepgram":"ok"}` — each value is `ok`, `error <status>`, or `unconfigured`.

### `GET /`
Serves the kiosk dashboard (`templates/index.html`).

## Content

### `GET /api/word-of-day`
Deterministic daily rotation from a curated list. Optional `?date=YYYY-MM-DD`.

```json
{"date":"2026-09-02","expression":"to push back (on)","kind":"phrasal_verb",
 "ipa":"/pʊʃ bæk/","register_tag":"Professional",
 "definition":"To resist or raise an objection…","examples":["…","…"]}
```

### `GET /api/news`
Three headlines (BBC / The Verge / The Guardian) fetched from RSS concurrently; a
failing feed is skipped. `vocab` is populated only when an LLM key is configured.

```json
{"headlines":[{"source":"BBC Technology","title":"…","link":"https://…",
  "published":"…","vocab":[{"term":"…","definition":"…"}]}]}
```

### `GET /api/podcast-digest`
Latest podcast episodes + a 3-paragraph brief + key terms (LLM, or summaries as
fallback).

```json
{"title":"Morning Brief","brief":["…","…","…"],
 "key_terms":[{"term":"…","definition":"…"}],
 "episodes":[{"title":"…","link":"…","published":"…","summary":"…","audio_url":"…"}]}
```

### `GET /api/word-of-day/entries`
The curated archive list: `[{"expression":"…","kind":"…","register_tag":"…"}, …]`.

### `GET /api/dictionary/lookup?word=<word>`
Click-to-translate lookup (LLM, cached 24 h).

```json
{"word":"resilient","ipa":"/rɪˈzɪl.i.ənt/","part_of_speech":"adjective",
 "synonyms":["tough","sturdy","robust"],"spanish":"resiliente","example":"…"}
```

### `GET /api/speech/connectors`
Returns the list of discourse connectors used for transcript highlighting.

## SRS

### `GET /api/srs/decks`
```json
[{"id":1,"slug":"workplace","name":"Workplace English","description":"…","due_count":12}]
```

### `GET /api/srs/decks/{deck_id}/due?limit=20`
Review cards (`repetitions > 0`) whose `due_at` has passed, ordered oldest-first.

### `GET /api/srs/decks/{deck_id}/new?limit=`
Unseen cards (`repetitions = 0`) to introduce, up to the limit (defaults to
`NEW_CARDS_PER_DAY`).

### `GET /api/srs/stats`
```json
{"cards_due":0,"cards_new":12,"cards_total":12,"reviews_today":0,"streak_days":0,"daily_goal":20}
```

### `GET /api/srs/export`
JSON backup of decks + cards: `{"decks":[…],"cards":[…]}`.

### `POST /api/srs/review`
Grade a card (1–4). Applies SM-2 atomically and records review history.

Request: `{"card_id":1,"grade":3}`
```json
{"card_id":1,"grade":3,"quality":4,"ease_factor":2.5,
 "interval_days":1,"repetitions":1,"due_at":"2026-09-03T22:45:40Z"}
```

### `POST /api/srs/cards`
Create a card (defaults to the first deck when `deck_id` is omitted).

Request: `{"front":"resilient","back":"resiliente","ipa":"/…/","register_tag":"","examples":["…"]}`
→ 201 with the created `CardOut`.

## PREP

### `GET /api/prep/scenario`
Random workplace scenario. `{"id":"scope_creep","context":"…","task":"…"}`

### `POST /api/prep/evaluate`
Evaluate a PREP response (LLM). `scenario` and `response` required; `elapsed_seconds`
optional (0–300).

```json
{"conciseness_score":70,"conciseness_feedback":"…","structure_score":90,
 "structure_feedback":"…","bluf_rewrite":"…","overall_feedback":"…"}
```

## Assist

### `POST /api/declutter`
Polish a draft (LLM). Request `{"draft":"…"}`.

```json
{"word_count_before":12,"word_count_after":7,"reduction_pct":41.7,
 "revised":"…","cut_phrases":["…"],"verb_upgrades":[{"weak":"…","strong":"…"}],
 "tone_assessment":"…"}
```

### `POST /api/voice/turn`
Roleplay partner turn (LLM). Request `{"scenario":"…","user_says":"…","history":[…]}`
(history capped server-side to the last 10 turns).

```json
{"partner_says":"…","follow_up_hint":"…"}
```

### `POST /api/quiz`
Generate a multiple-choice comprehension question (LLM). Request `{"text":"…"}`.

```json
{"question":"…","correct_answer":"…","distractors":["…","…","…"]}
```

### `POST /api/register/rewrite`
Rewrite a sentence in a target register (LLM). Request
`{"text":"…","register_tag":"Executive"}`. Tags: `Executive` / `Informal` /
`Technical` / `Polite` / `Hedged`.

```json
{"rewritten":"…"}
```

### `POST /api/writing/correct`
Correct grammar, usage, punctuation, and word choice (LLM), returning the
corrected text and a per-error explanation list. Request `{"draft":"…"}`.

```json
{"corrected":"He went…","corrections":[{"original":"He go","corrected":"He went",
  "explanation":"Use the past simple…"}],"error_count":1}
```

### `GET /api/speech/topics`
Curated monologue topics (deterministic, no LLM): `["Describe a project…", …]`.

### `POST /api/speech/monologue/evaluate`
Evaluate a recorded monologue (LLM). Request
`{"topic":"…","transcript":"…","duration_seconds":60}`.

```json
{"structure_score":70,"fluency_score":65,"vocabulary_score":80,"grammar_score":75,
 "strengths":["…"],"improvements":["…"],"model_answer":"…"}
```

## Learning (grammar & pronunciation)

### `GET /api/grammar/irregular-verbs`
Curated irregular verbs (deterministic, no LLM):
`[{"base":"begin","past":"began","participle":"begun"}, …]`.

### `GET /api/grammar/drill?kind=<phrasal_verb|collocation|use_of_english>`
LLM multiple-choice cloze with one gap and four options.

```json
{"sentence":"The board decided to ___ the merger.","options":["push back on","rule out",
 "phase out","break down"],"answer":"push back on","explanation":"…"}
```

### `GET /api/grammar/word-forms`
LLM gap-fill requiring the correct derived form of a root word.

```json
{"sentence":"The ___ was final.","root":"decide","answer":"decision","explanation":"…"}
```

### `GET /api/grammar/rule-of-day`
Deterministic daily grammar rule (no LLM). Optional `?date=YYYY-MM-DD`.

```json
{"id":"third-conditional","title":"Third conditional (past regret)","rule":"…",
 "examples":["…","…"],"common_error":"…"}
```

### `POST /api/grammar/coach`
Free-form grammar question → LLM answer. Request `{"question":"…"}`.

```json
{"answer":"Use the present perfect for a past action with present relevance…"}
```

### `GET /api/pronunciation/minimal-pairs`
Curated minimal pairs (deterministic, no LLM):
`[{"a":"ship","b":"sheep","ipa_a":"/ʃɪp/","ipa_b":"/ʃiːp/"}, …]`.

### `GET /api/pronunciation/pitfalls`
Curated Spanish-speaker pronunciation pitfalls (deterministic, no LLM):
`[{"issue":"/v/ vs /b/","tip":"…"}, …]`.

## Plan

### `POST /api/plan/weekly`
Generate a personalized seven-day plan (LLM). Request
`{"goal":"…","minutes_per_day":30,"focus_areas":["Speaking","Grammar"]}`.

```json
{"days":[{"day":"Monday","activity":"…","duration_minutes":45}, …],"tip":"…"}
```

### `GET /api/radio/stations`
```json
[{"id":"npr","name":"NPR News","stream_url":"https://…","format":"mp3"},
 {"id":"bbc-radio-4","name":"BBC Radio 4","stream_url":"https://…","format":"mp3"}]
```

### `POST /api/radio/transcribe`
Transcribe a remote audio URL and highlight connectors. Uses Deepgram by default;
set `STT_PROVIDER=whisper` to route through a local whisper.cpp server instead
(same request/response shape).

Request `{"audio_url":"https://…"}` (http/https only; optional `DEEPGRAM_ALLOWED_HOSTS`).
```json
{"text":"However, …","highlights":[{"connector":"however","index":0}]}
```

## WebSockets

### `/ws` — dashboard broadcast bus
- Server → client on connect: `{"type":"hello"}`
- Server → client heartbeat: `{"type":"ping"}` every 25 s; client must reply
  `{"type":"pong"}` or the peer is evicted after 60 s.
- Client → server: `{"type":"ping"}` answered with `{"type":"pong"}`.
- Server → client broadcasts, e.g. `{"type":"radio:transcript","text":"…","final":true}`.

### `/ws/radio` — live transcription relay
- Client sends a JSON text frame `{"type":"start","sample_rate":48000}` to open a
  Deepgram live session.
- Client streams **raw binary** 16-bit little-endian mono PCM frames.
- Client sends `{"type":"stop"}` (or closes) to end.
- Transcripts are broadcast to `/ws` clients as `radio:transcript` messages.
- On failure, server sends `{"type":"error","detail":"…"}`.
