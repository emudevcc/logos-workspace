"""Endpoint tests for the spaced-repetition router."""

from __future__ import annotations

from tests.backend.helpers import ClientFactory


def test_list_decks_returns_seeded_deck(client_factory: ClientFactory) -> None:
    with client_factory() as client:
        response = client.get("/api/srs/decks")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["slug"] == "workplace"
        assert data[0]["due_count"] == 0


def test_new_cards_and_review_flow(client_factory: ClientFactory) -> None:
    with client_factory() as client:
        deck_id = client.get("/api/srs/decks").json()[0]["id"]
        new_cards = client.get(f"/api/srs/decks/{deck_id}/new").json()
        assert new_cards

        response = client.post("/api/srs/review", json={"card_id": new_cards[0]["id"], "grade": 3})
        assert response.status_code == 200
        body = response.json()
        assert body["interval_days"] == 1
        assert body["repetitions"] == 1


def test_review_unknown_card_returns_404(client_factory: ClientFactory) -> None:
    with client_factory() as client:
        response = client.post("/api/srs/review", json={"card_id": 999999, "grade": 3})
        assert response.status_code == 404


def test_review_rejects_invalid_grade(client_factory: ClientFactory) -> None:
    with client_factory() as client:
        response = client.post("/api/srs/review", json={"card_id": 1, "grade": 9})
        assert response.status_code == 422


def test_create_card_endpoint(client_factory: ClientFactory) -> None:
    with client_factory() as client:
        response = client.post("/api/srs/cards", json={"front": "hello", "back": "hola"})
        assert response.status_code == 201
        assert response.json()["front"] == "hello"


def test_stats_endpoint(client_factory: ClientFactory) -> None:
    with client_factory() as client:
        response = client.get("/api/srs/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["cards_total"] == 12
        assert data["cards_new"] == 12
        assert data["cards_due"] == 0


def test_export_endpoint(client_factory: ClientFactory) -> None:
    with client_factory() as client:
        response = client.get("/api/srs/export")
        assert response.status_code == 200
        data = response.json()
        assert len(data["decks"]) == 1
        assert len(data["cards"]) == 12
