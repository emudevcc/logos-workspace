"""Minimal async-safe TTL cache for expensive external content.

Single-value-per-key with in-flight request coalescing, so concurrent requests
for the same key share one fetch instead of stampeding the upstream API.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Generic, TypeVar

T = TypeVar("T")


class TTLCache(Generic[T]):
    def __init__(self, ttl_seconds: float) -> None:
        self._ttl = ttl_seconds
        self._values: dict[str, tuple[float, T]] = {}
        self._in_flight: dict[str, asyncio.Future[T]] = {}

    async def get(self, key: str, factory: Callable[[], Awaitable[T]]) -> T:
        now = time.monotonic()
        cached = self._values.get(key)
        if cached is not None and now - cached[0] < self._ttl:
            return cached[1]

        in_flight = self._in_flight.get(key)
        if in_flight is not None:
            return await in_flight

        future = asyncio.ensure_future(factory())
        self._in_flight[key] = future
        try:
            value = await future
        except BaseException:
            raise
        finally:
            self._in_flight.pop(key, None)

        self._values[key] = (time.monotonic(), value)
        return value

    def put(self, key: str, value: T) -> None:
        """Store a freshly computed value (e.g. after a forced refresh)."""
        self._values[key] = (time.monotonic(), value)
