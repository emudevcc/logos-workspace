"""Unit tests for the Deepgram client."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx
import pytest

from app.services.deepgram import (
    DeepgramClient,
    DeepgramError,
    DeepgramNotConfiguredError,
)

Handler = Callable[[httpx.Request], httpx.Response]


def _client(handler: Handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _response() -> dict[str, Any]:
    return {
        "results": {
            "channels": [
                {
                    "alternatives": [
                        {
                            "transcript": "hello world",
                            "words": [{"word": "hello", "start": 0.0, "end": 0.5}],
                        }
                    ]
                }
            ]
        }
    }


async def test_transcribe_url_parses_transcript() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_response())

    async with _client(handler) as http:
        deepgram = DeepgramClient(http, api_key="k")
        result = await deepgram.transcribe_url("https://e.com/a.mp3")
    assert result.text == "hello world"
    assert result.words[0].word == "hello"


async def test_not_configured_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200)

    async with _client(handler) as http:
        deepgram = DeepgramClient(http, api_key="")
        assert deepgram.enabled is False
        with pytest.raises(DeepgramNotConfiguredError):
            await deepgram.transcribe_url("https://e.com/a.mp3")


async def test_5xx_raises() -> None:
    async with _client(lambda r: httpx.Response(500)) as http:
        deepgram = DeepgramClient(http, api_key="k")
        with pytest.raises(DeepgramError):
            await deepgram.transcribe_url("https://e.com/a.mp3")


async def test_4xx_raises() -> None:
    async with _client(lambda r: httpx.Response(400, text="bad")) as http:
        deepgram = DeepgramClient(http, api_key="k")
        with pytest.raises(DeepgramError):
            await deepgram.transcribe_url("https://e.com/a.mp3")


async def test_malformed_shape_raises() -> None:
    async with _client(lambda r: httpx.Response(200, json={"nope": 1})) as http:
        deepgram = DeepgramClient(http, api_key="k")
        with pytest.raises(DeepgramError):
            await deepgram.transcribe_url("https://e.com/a.mp3")
