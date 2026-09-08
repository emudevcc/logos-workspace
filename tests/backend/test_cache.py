"""Unit tests for the TTL cache."""

import asyncio

import pytest

from app.core.cache import TTLCache


async def test_cache_returns_and_reuses_value() -> None:
    cache = TTLCache[int](ttl_seconds=60.0)
    calls = 0

    async def factory() -> int:
        nonlocal calls
        calls += 1
        return 42

    assert await cache.get("k", factory) == 42
    assert await cache.get("k", factory) == 42
    assert calls == 1


async def test_cache_coalesces_in_flight_fetches() -> None:
    cache = TTLCache[int](ttl_seconds=60.0)
    calls = 0

    async def factory() -> int:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.01)
        return 7

    results = await asyncio.gather(cache.get("k", factory), cache.get("k", factory))
    assert list(results) == [7, 7]
    assert calls == 1


async def test_cache_expires_after_ttl() -> None:
    cache = TTLCache[int](ttl_seconds=0.0)
    calls = 0

    async def factory() -> int:
        nonlocal calls
        calls += 1
        return calls

    assert await cache.get("k", factory) == 1
    assert await cache.get("k", factory) == 2
    assert calls == 2


async def test_put_overrides_cached_value() -> None:
    cache = TTLCache[int](ttl_seconds=60.0)
    calls = 0

    async def factory() -> int:
        nonlocal calls
        calls += 1
        return calls

    assert await cache.get("k", factory) == 1
    cache.put("k", 99)
    assert await cache.get("k", factory) == 99
    assert calls == 1


async def test_cache_does_not_cache_failures() -> None:
    cache = TTLCache[int](ttl_seconds=60.0)
    calls = 0

    async def factory() -> int:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("boom")
        return 9

    with pytest.raises(RuntimeError):
        await cache.get("k", factory)
    assert await cache.get("k", factory) == 9
    assert calls == 2
