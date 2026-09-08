"""WebSocket connection registry, broadcaster, and liveness heartbeat.

A single ``ConnectionManager`` instance lives on ``app.state`` for the process
lifetime. It tracks every open socket, fans out broadcasts, and evicts peers
that stop answering pings so dead sockets never accumulate and clients can
reconnect cheaply.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from contextlib import suppress
from typing import Any, Protocol

logger = logging.getLogger(__name__)

Clock = Callable[[], float]

HEARTBEAT_INTERVAL = 25.0
HEARTBEAT_TIMEOUT = 60.0


class ConnectionLimitError(Exception):
    """Raised when the connection cap is exceeded."""


class WebSocketPeer(Protocol):
    """Minimal interface the manager needs from a WebSocket connection.

    Declared as a ``Protocol`` so the manager can be unit-tested with in-memory
    fakes while still type-checking against Starlette's real ``WebSocket``.
    """

    async def accept(self) -> None: ...
    async def send_json(self, data: Any) -> None: ...
    async def close(self, code: int = 1000, reason: str | None = None) -> None: ...


class ConnectionManager:
    def __init__(
        self,
        *,
        heartbeat_interval: float = HEARTBEAT_INTERVAL,
        heartbeat_timeout: float = HEARTBEAT_TIMEOUT,
        clock: Clock = time.monotonic,
        max_connections: int = 100,
    ) -> None:
        if heartbeat_interval <= 0:
            raise ValueError("heartbeat_interval must be positive")
        if heartbeat_timeout <= 0:
            raise ValueError("heartbeat_timeout must be positive")
        if max_connections <= 0:
            raise ValueError("max_connections must be positive")
        self._heartbeat_interval = heartbeat_interval
        self._heartbeat_timeout = heartbeat_timeout
        self._clock = clock
        self._max_connections = max_connections
        self._peers: dict[WebSocketPeer, float] = {}

    @property
    def size(self) -> int:
        return len(self._peers)

    async def connect(self, peer: WebSocketPeer) -> None:
        if len(self._peers) >= self._max_connections:
            await self._close_peer(peer)
            raise ConnectionLimitError("connection limit reached")
        await peer.accept()
        await peer.send_json({"type": "hello"})
        self._peers[peer] = self._clock()

    def disconnect(self, peer: WebSocketPeer) -> None:
        self._peers.pop(peer, None)

    def touch(self, peer: WebSocketPeer) -> None:
        if peer in self._peers:
            self._peers[peer] = self._clock()

    async def send_json(self, peer: WebSocketPeer, message: dict[str, Any]) -> bool:
        try:
            await peer.send_json(message)
            return True
        except Exception:
            await self._evict(peer)
            return False

    async def broadcast(self, message: dict[str, Any]) -> int:
        delivered = 0
        for peer in list(self._peers):
            if await self.send_json(peer, message):
                delivered += 1
        return delivered

    async def heartbeat_once(self) -> None:
        now = self._clock()
        stale = [
            peer
            for peer, last_seen in self._peers.items()
            if now - last_seen > self._heartbeat_timeout
        ]
        for peer in stale:
            await self._evict(peer)
        for peer in list(self._peers):
            await self.send_json(peer, {"type": "ping"})

    async def heartbeat_loop(self) -> None:
        while True:
            await asyncio.sleep(self._heartbeat_interval)
            try:
                await self.heartbeat_once()
            except Exception:
                logger.exception("WebSocket heartbeat tick failed")

    async def close_all(self) -> None:
        for peer in list(self._peers):
            await self._close_peer(peer)
        self._peers.clear()

    async def _evict(self, peer: WebSocketPeer) -> None:
        self._peers.pop(peer, None)
        await self._close_peer(peer)

    async def _close_peer(self, peer: WebSocketPeer) -> None:
        with suppress(Exception):
            await peer.close()
