"""Endpoint tests for the assist router (de-clutter, voice, radio, speech)."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app
from app.services.deepgram import DeepgramTranscript
from tests.backend.helpers import ClientFactory, FakeDeepgram, FakeLLM


def test_declutter_endpoint(client_factory: ClientFactory) -> None:
    llm = FakeLLM(
        result={
            "revised": "Tight version.",
            "cut_phrases": [],
            "verb_upgrades": [],
            "tone": "direct",
        }
    )
    with client_factory(llm=llm) as client:
        response = client.post(
            "/api/declutter",
            json={"draft": "In order to proceed with this matter in a careful manner."},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["word_count_before"] > data["word_count_after"]


def test_voice_turn_endpoint(client_factory: ClientFactory) -> None:
    llm = FakeLLM(result={"partner_says": "Sure.", "follow_up_hint": ""})
    with client_factory(llm=llm) as client:
        response = client.post("/api/voice/turn", json={"scenario": "s", "user_says": "u"})
        assert response.status_code == 200
        assert response.json()["partner_says"] == "Sure."


def test_radio_stations_endpoint(client_factory: ClientFactory) -> None:
    with client_factory() as client:
        response = client.get("/api/radio/stations")
        assert response.status_code == 200
        assert len(response.json()) >= 1


def test_radio_transcribe_endpoint(client_factory: ClientFactory) -> None:
    deepgram = FakeDeepgram(transcript=DeepgramTranscript(text="However, yes.", words=[]))
    with client_factory(deepgram=deepgram) as client:
        response = client.post("/api/radio/transcribe", json={"audio_url": "https://e.com/a.mp3"})
        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "However, yes."
        assert data["highlights"][0]["connector"] == "however"


def test_radio_transcribe_not_configured_returns_503(client_factory: ClientFactory) -> None:
    with client_factory(deepgram=FakeDeepgram(enabled=False)) as client:
        response = client.post("/api/radio/transcribe", json={"audio_url": "https://e.com/a.mp3"})
        assert response.status_code == 503


def test_radio_transcribe_rejects_non_http_scheme(client_factory: ClientFactory) -> None:
    with client_factory(deepgram=FakeDeepgram()) as client:
        response = client.post("/api/radio/transcribe", json={"audio_url": "javascript:alert(1)"})
        assert response.status_code == 422


def test_radio_transcribe_rejects_disallowed_host(tmp_path: Path) -> None:
    os.environ["COCKPIT_DB"] = str(tmp_path / "db.sqlite")
    os.environ["DEEPGRAM_ALLOWED_HOSTS"] = '["allowed.example.com"]'
    get_settings.cache_clear()

    app = create_app(deepgram=FakeDeepgram())
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/radio/transcribe", json={"audio_url": "https://evil.example.com/a.mp3"}
            )
            assert response.status_code == 400
    finally:
        get_settings.cache_clear()
        os.environ.pop("COCKPIT_DB", None)
        os.environ.pop("DEEPGRAM_ALLOWED_HOSTS", None)


def test_speech_connectors_endpoint(client_factory: ClientFactory) -> None:
    with client_factory() as client:
        response = client.get("/api/speech/connectors")
        assert response.status_code == 200
        assert "furthermore" in response.json()


def test_writing_correct_endpoint(client_factory: ClientFactory) -> None:
    llm = FakeLLM(
        result={
            "corrected": "He goes.",
            "corrections": [
                {"original": "He go", "corrected": "He goes", "explanation": "3rd person"}
            ],
        }
    )
    with client_factory(llm=llm) as client:
        response = client.post("/api/writing/correct", json={"draft": "He go."})
        assert response.status_code == 200
        data = response.json()
        assert data["corrected"] == "He goes."
        assert data["error_count"] == 1


def test_speech_topics_endpoint(client_factory: ClientFactory) -> None:
    with client_factory() as client:
        response = client.get("/api/speech/topics")
        assert response.status_code == 200
        assert len(response.json()) >= 6


def test_monologue_evaluate_endpoint(client_factory: ClientFactory) -> None:
    llm = FakeLLM(
        result={
            "structure_score": 70,
            "fluency_score": 60,
            "vocabulary_score": 80,
            "grammar_score": 75,
            "strengths": ["Clear"],
            "improvements": ["Cut fillers"],
            "model_answer": "A model answer.",
        }
    )
    with client_factory(llm=llm) as client:
        response = client.post(
            "/api/speech/monologue/evaluate",
            json={"topic": "t", "transcript": "I spoke.", "duration_seconds": 60},
        )
        assert response.status_code == 200
        assert response.json()["structure_score"] == 70


def test_weekly_plan_endpoint(client_factory: ClientFactory) -> None:
    llm = FakeLLM(
        result={
            "days": [{"day": "Monday", "activity": "Speak", "duration_minutes": 30}],
            "tip": "Keep going.",
        }
    )
    with client_factory(llm=llm) as client:
        response = client.post(
            "/api/plan/weekly",
            json={"goal": "fluency", "minutes_per_day": 30, "focus_areas": ["Speaking"]},
        )
        assert response.status_code == 200
        assert response.json()["days"][0]["day"] == "Monday"
