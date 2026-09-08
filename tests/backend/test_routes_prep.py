"""Endpoint tests for the PREP router."""

from __future__ import annotations

from tests.backend.helpers import ClientFactory, FakeLLM


def test_scenario_endpoint(client_factory: ClientFactory) -> None:
    with client_factory() as client:
        response = client.get("/api/prep/scenario")
        assert response.status_code == 200
        data = response.json()
        assert data["id"]
        assert data["context"]
        assert data["task"]


def test_evaluate_endpoint(client_factory: ClientFactory) -> None:
    llm = FakeLLM(
        result={
            "conciseness_score": 80,
            "conciseness_feedback": "tight",
            "structure_score": 75,
            "structure_feedback": "clear PREP",
            "bluf_rewrite": "Bottom line first.",
            "overall_feedback": "good",
        }
    )
    with client_factory(llm=llm) as client:
        response = client.post("/api/prep/evaluate", json={"scenario": "s", "response": "r"})
        assert response.status_code == 200
        assert response.json()["structure_score"] == 75


def test_evaluate_not_configured_returns_503(client_factory: ClientFactory) -> None:
    with client_factory(llm=FakeLLM(enabled=False)) as client:
        response = client.post("/api/prep/evaluate", json={"scenario": "s", "response": "r"})
        assert response.status_code == 503


def test_evaluate_invalid_payload_returns_422(client_factory: ClientFactory) -> None:
    with client_factory() as client:
        response = client.post("/api/prep/evaluate", json={"scenario": "", "response": "r"})
        assert response.status_code == 422
