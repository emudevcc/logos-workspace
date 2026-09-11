"""Unit tests for the Groq LLM client."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime

import httpx
import pytest

from app.services.llm import LLMClient, LLMError, LLMJsonValidationError, _retry_after_seconds
from tests.backend.helpers import chat_error_response, chat_response

Handler = Callable[[httpx.Request], httpx.Response]


def _client(handler: Handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _capture_sleeps(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Monkeypatch the sleep reference *inside* llm.py and record each call."""
    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr("app.services.llm.asyncio.sleep", fake_sleep)
    return sleeps


async def test_complete_json_returns_parsed_object() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=chat_response('{"ok": true}'))

    async with _client(handler) as http:
        llm = LLMClient(
            http, base_url="https://api.example.com", api_key="k", model="m", max_retries=0
        )
        result = await llm.complete_json(system="s", user="u")
    assert result == {"ok": True}


async def test_retries_on_transient_5xx_then_succeeds() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(500)
        return httpx.Response(200, json=chat_response('{"ok": true}'))

    async with _client(handler) as http:
        llm = LLMClient(
            http, base_url="https://api.example.com", api_key="k", model="m", max_retries=1
        )
        result = await llm.complete_json(system="s", user="u")
    assert result == {"ok": True}
    assert calls == 2


async def test_4xx_raises_llm_error_without_retry() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(400, text="bad request")

    async with _client(handler) as http:
        llm = LLMClient(
            http, base_url="https://api.example.com", api_key="k", model="m", max_retries=2
        )
        with pytest.raises(LLMError):
            await llm.complete_json(system="s", user="u")
    assert calls == 1


async def test_disabled_when_no_api_key() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200)

    async with _client(handler) as http:
        llm = LLMClient(http, base_url="https://api.example.com", api_key="", model="m")
        assert llm.enabled is False
        with pytest.raises(LLMError):
            await llm.complete_json(system="s", user="u")


async def test_invalid_json_content_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=chat_response("not json"))

    async with _client(handler) as http:
        llm = LLMClient(
            http, base_url="https://api.example.com", api_key="k", model="m", max_retries=0
        )
        with pytest.raises(LLMJsonValidationError):
            await llm.complete_json(system="s", user="u")


async def test_non_object_json_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=chat_response("[1, 2, 3]"))

    async with _client(handler) as http:
        llm = LLMClient(
            http, base_url="https://api.example.com", api_key="k", model="m", max_retries=0
        )
        with pytest.raises(LLMJsonValidationError):
            await llm.complete_json(system="s", user="u")


async def test_json_validate_failed_400_raises_typed_error() -> None:
    """Groq's structured json_validate_failed 400 maps to the typed exception."""
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return chat_error_response(400, "json_validate_failed")

    async with _client(handler) as http:
        llm = LLMClient(
            http, base_url="https://api.example.com", api_key="k", model="m", max_retries=2
        )
        with pytest.raises(LLMJsonValidationError):
            await llm.complete_json(system="s", user="u")
    # A 400 is never retried at this layer, typed or not.
    assert calls == 1


async def test_unrelated_400_raises_base_llm_error() -> None:
    """A 400 with no JSON-failure signal stays a plain LLMError."""

    def handler(request: httpx.Request) -> httpx.Response:
        return chat_error_response(400, "invalid_request_error")

    async with _client(handler) as http:
        llm = LLMClient(
            http, base_url="https://api.example.com", api_key="k", model="m", max_retries=2
        )
        with pytest.raises(LLMError) as excinfo:
            await llm.complete_json(system="s", user="u")
    assert not isinstance(excinfo.value, LLMJsonValidationError)


async def test_json_failure_substring_fallback_raises_typed_error() -> None:
    """A provider body with no error.code still classifies via the fallback."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, text="Failed to generate JSON: {}")

    async with _client(handler) as http:
        llm = LLMClient(
            http, base_url="https://api.example.com", api_key="k", model="m", max_retries=0
        )
        with pytest.raises(LLMJsonValidationError):
            await llm.complete_json(system="s", user="u")


async def test_429_with_retry_after_sleeps_exactly_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An honored Retry-After must not also pay the next iteration's backoff."""
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, headers={"retry-after": "3"})
        return httpx.Response(200, json=chat_response('{"ok": true}'))

    sleeps = _capture_sleeps(monkeypatch)
    async with _client(handler) as http:
        llm = LLMClient(
            http, base_url="https://api.example.com", api_key="k", model="m", max_retries=1
        )
        result = await llm.complete_json(system="s", user="u")
    assert result == {"ok": True}
    assert calls == 2
    assert sleeps == [3.0]


async def test_429_without_retry_after_uses_backoff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No usable Retry-After header -> exactly one jittered backoff sleep."""
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429)
        return httpx.Response(200, json=chat_response('{"ok": true}'))

    sleeps = _capture_sleeps(monkeypatch)
    async with _client(handler) as http:
        llm = LLMClient(
            http, base_url="https://api.example.com", api_key="k", model="m", max_retries=1
        )
        result = await llm.complete_json(system="s", user="u")
    assert result == {"ok": True}
    assert len(sleeps) == 1
    assert sleeps[0] <= 4.0


async def test_transport_error_still_uses_backoff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The honored-Retry-After gate must not swallow the 5xx/transport backoff."""
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(500)
        return httpx.Response(200, json=chat_response('{"ok": true}'))

    sleeps = _capture_sleeps(monkeypatch)
    async with _client(handler) as http:
        llm = LLMClient(
            http, base_url="https://api.example.com", api_key="k", model="m", max_retries=1
        )
        result = await llm.complete_json(system="s", user="u")
    assert result == {"ok": True}
    assert len(sleeps) == 1
    assert sleeps[0] <= 4.0


def _retry_after_response(value: str | None) -> httpx.Response:
    headers = {"retry-after": value} if value is not None else {}
    return httpx.Response(429, headers=headers)


def test_retry_after_seconds_parses_delta_seconds() -> None:
    assert _retry_after_seconds(_retry_after_response("3")) == 3.0
    assert _retry_after_seconds(_retry_after_response("  7  ")) == 7.0
    assert _retry_after_seconds(_retry_after_response("0")) == 0.0


def test_retry_after_seconds_parses_http_date() -> None:
    moment = datetime.now(UTC) + timedelta(seconds=30)
    http_date = format_datetime(moment, usegmt=True)
    value = _retry_after_seconds(_retry_after_response(http_date))
    assert value is not None
    # Parsed to a remaining-seconds delay, allowing for elapsed wall time.
    assert 25.0 <= value <= 31.0


def test_retry_after_seconds_clamps_past_http_date_to_zero() -> None:
    past = format_datetime(datetime.now(UTC) - timedelta(seconds=60), usegmt=True)
    assert _retry_after_seconds(_retry_after_response(past)) == 0.0


def test_retry_after_seconds_returns_none_when_unusable() -> None:
    assert _retry_after_seconds(_retry_after_response(None)) is None
    assert _retry_after_seconds(_retry_after_response("")) is None
    assert _retry_after_seconds(_retry_after_response("   ")) is None
    # Unparsable / non-numeric non-date values fall back to the caller's backoff.
    assert _retry_after_seconds(_retry_after_response("soon")) is None
    assert _retry_after_seconds(_retry_after_response("-5")) is None
    assert _retry_after_seconds(object()) is None  # no .headers attribute


async def test_429_with_unparsable_retry_after_uses_backoff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unusable Retry-After must fall back to one jittered backoff sleep."""
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return _retry_after_response("not-a-delay")
        return httpx.Response(200, json=chat_response('{"ok": true}'))

    sleeps = _capture_sleeps(monkeypatch)
    async with _client(handler) as http:
        llm = LLMClient(
            http, base_url="https://api.example.com", api_key="k", model="m", max_retries=1
        )
        result = await llm.complete_json(system="s", user="u")
    assert result == {"ok": True}
    assert len(sleeps) == 1
    assert sleeps[0] <= 4.0


async def test_429_retry_after_above_cap_uses_backoff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A Retry-After longer than the 15s honor cap falls back to the backoff."""
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return _retry_after_response("99")
        return httpx.Response(200, json=chat_response('{"ok": true}'))

    sleeps = _capture_sleeps(monkeypatch)
    async with _client(handler) as http:
        llm = LLMClient(
            http, base_url="https://api.example.com", api_key="k", model="m", max_retries=1
        )
        result = await llm.complete_json(system="s", user="u")
    assert result == {"ok": True}
    assert len(sleeps) == 1
    assert sleeps[0] <= 4.0
