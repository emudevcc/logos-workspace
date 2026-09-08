"""Endpoint tests for the curated learning routes."""

from __future__ import annotations

from tests.backend.helpers import ClientFactory, FakeLLM


def test_irregular_verbs_endpoint(client_factory: ClientFactory) -> None:
    with client_factory() as client:
        response = client.get("/api/grammar/irregular-verbs")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 100
        assert data[0]["base"] and data[0]["past"] and data[0]["participle"]


def test_minimal_pairs_endpoint(client_factory: ClientFactory) -> None:
    with client_factory() as client:
        response = client.get("/api/pronunciation/minimal-pairs")
        assert response.status_code == 200
        assert len(response.json()) >= 40


def test_pitfalls_endpoint(client_factory: ClientFactory) -> None:
    with client_factory() as client:
        response = client.get("/api/pronunciation/pitfalls")
        assert response.status_code == 200
        assert len(response.json()) >= 8


def test_rule_of_day_endpoint(client_factory: ClientFactory) -> None:
    with client_factory() as client:
        response = client.get("/api/grammar/rule-of-day")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] and data["rule"] and data["examples"]


def test_grammar_drill_endpoint(client_factory: ClientFactory) -> None:
    llm = FakeLLM(
        result={
            "sentence": "We need to ___ the risk.",
            "options": ["rule out", "run out", "rule in", "run in"],
            "answer": "rule out",
            "explanation": "Eliminate.",
        }
    )
    with client_factory(llm=llm) as client:
        response = client.get("/api/grammar/drill", params={"kind": "phrasal_verb"})
        assert response.status_code == 200
        assert response.json()["answer"] == "rule out"


def test_grammar_drill_rejects_bad_kind(client_factory: ClientFactory) -> None:
    with client_factory() as client:
        response = client.get("/api/grammar/drill", params={"kind": "nonsense"})
        assert response.status_code == 422


def test_word_forms_endpoint(client_factory: ClientFactory) -> None:
    llm = FakeLLM(
        result={
            "sentence": "The ___ was final.",
            "root": "decide",
            "answer": "decision",
            "explanation": "Noun.",
        }
    )
    with client_factory(llm=llm) as client:
        response = client.get("/api/grammar/word-forms")
        assert response.status_code == 200
        assert response.json()["answer"] == "decision"


def test_grammar_coach_endpoint(client_factory: ClientFactory) -> None:
    llm = FakeLLM(result={"answer": "Use the present perfect for relevance."})
    with client_factory(llm=llm) as client:
        response = client.post(
            "/api/grammar/coach", json={"question": "Present perfect vs past simple?"}
        )
        assert response.status_code == 200
        assert response.json()["answer"]


def test_pronunciation_sentence_endpoint(client_factory: ClientFactory) -> None:
    llm = FakeLLM(result={"sentence": "A fresh simple sentence."})
    with client_factory(llm=llm) as client:
        response = client.get("/api/pronunciation/sentence")
        assert response.status_code == 200
        assert response.json()["sentence"] == "A fresh simple sentence."
