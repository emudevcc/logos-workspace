"""End-to-end WebSocket endpoint tests (isolated per-test database)."""

from tests.backend.helpers import ClientFactory


def test_websocket_accepts_and_greets(client_factory: ClientFactory) -> None:
    with client_factory() as client, client.websocket_connect("/ws") as websocket:
        assert websocket.receive_json() == {"type": "hello"}


def test_websocket_ping_is_answered_with_pong(client_factory: ClientFactory) -> None:
    with client_factory() as client, client.websocket_connect("/ws") as websocket:
        websocket.receive_json()  # hello
        websocket.send_json({"type": "ping"})
        assert websocket.receive_json() == {"type": "pong"}


def test_healthz_reports_ok(client_factory: ClientFactory) -> None:
    with client_factory() as client:
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
