"""Unit tests for the WebSocket connection manager and broadcaster."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from app.core.ws_manager import ConnectionLimitError, ConnectionManager


class FakeClock:
    """Injectable monotonic clock whose value a test advances manually."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class FakePeer:
    """In-memory stand-in for Starlette's WebSocket."""

    def __init__(self, *, fail_on_send: bool = False) -> None:
        self.fail_on_send = fail_on_send
        self.accepted = False
        self.closed = False
        self.close_code: int | None = None
        self.sent: list[dict[str, Any]] = []

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, data: Any) -> None:
        if self.fail_on_send:
            raise ConnectionError("socket closed")
        self.sent.append(data)

    async def close(self, code: int = 1000, reason: str | None = None) -> None:
        self.closed = True
        self.close_code = code


async def test_connect_accepts_and_greets() -> None:
    manager = ConnectionManager()
    peer = FakePeer()
    await manager.connect(peer)
    assert peer.accepted is True
    assert manager.size == 1
    assert peer.sent == [{"type": "hello"}]


async def test_disconnect_removes_peer() -> None:
    manager = ConnectionManager()
    peer = FakePeer()
    await manager.connect(peer)
    manager.disconnect(peer)
    assert manager.size == 0


async def test_broadcast_delivers_to_all_peers() -> None:
    manager = ConnectionManager()
    first = FakePeer()
    second = FakePeer()
    await manager.connect(first)
    await manager.connect(second)
    delivered = await manager.broadcast({"type": "news", "items": []})
    assert delivered == 2
    assert {"type": "news", "items": []} in first.sent
    assert {"type": "news", "items": []} in second.sent


async def test_broadcast_evicts_failed_peer() -> None:
    manager = ConnectionManager()
    healthy = FakePeer()
    broken = FakePeer()
    await manager.connect(healthy)
    await manager.connect(broken)
    broken.fail_on_send = True
    delivered = await manager.broadcast({"type": "ping"})
    assert delivered == 1
    assert manager.size == 1
    assert broken.closed is True


async def test_touch_updates_liveness() -> None:
    clock = FakeClock()
    manager = ConnectionManager(heartbeat_timeout=60.0, clock=clock)
    peer = FakePeer()
    await manager.connect(peer)
    clock.now = 30.0
    manager.touch(peer)
    await manager.heartbeat_once()
    assert manager.size == 1


async def test_heartbeat_evicts_stale_peer() -> None:
    clock = FakeClock()
    manager = ConnectionManager(heartbeat_timeout=60.0, clock=clock)
    peer = FakePeer()
    await manager.connect(peer)
    clock.now = 61.0
    await manager.heartbeat_once()
    assert manager.size == 0
    assert peer.closed is True


async def test_heartbeat_pings_active_peers() -> None:
    manager = ConnectionManager()
    peer = FakePeer()
    await manager.connect(peer)
    peer.sent.clear()  # drop the hello message
    await manager.heartbeat_once()
    assert {"type": "ping"} in peer.sent


async def test_heartbeat_loop_can_be_cancelled() -> None:
    manager = ConnectionManager(heartbeat_interval=0.01)
    task = asyncio.create_task(manager.heartbeat_loop())
    await asyncio.sleep(0.03)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


async def test_connect_rejects_over_capacity() -> None:
    manager = ConnectionManager(max_connections=1)
    first = FakePeer()
    await manager.connect(first)

    second = FakePeer()
    with pytest.raises(ConnectionLimitError):
        await manager.connect(second)

    assert second.closed is True
    assert manager.size == 1
