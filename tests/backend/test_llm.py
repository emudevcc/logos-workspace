"""Unit tests for the Groq LLM client."""

from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest

from app.services.llm import LLMClient, LLMError
from tests.backend.helpers import chat_response

Handler = Callable[[httpx.Request], httpx.Response]


def _client(handler: Handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


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
        with pytest.raises(LLMError):
            await llm.complete_json(system="s", user="u")


async def test_non_object_json_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=chat_response("[1, 2, 3]"))

    async with _client(handler) as http:
        llm = LLMClient(
            http, base_url="https://api.example.com", api_key="k", model="m", max_retries=0
        )
        with pytest.raises(LLMError):
            await llm.complete_json(system="s", user="u")
