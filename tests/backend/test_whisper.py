"""Tests for the local whisper.cpp STT client."""

from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest

from app.services.whisper import WhisperClient, WhisperError, WhisperNotConfiguredError
from tests.backend.helpers import make_mock_http

Handler = Callable[[httpx.Request], httpx.Response]


def _noop(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200)


def _client(handler: Handler, base_url: str = "http://whisper.local") -> WhisperClient:
    return WhisperClient(make_mock_http(handler), base_url=base_url)


async def test_transcribe_url_returns_text() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/audio.mp3":
            return httpx.Response(200, content=b"fake-audio-bytes")
        if request.url.path == "/inference":
            return httpx.Response(200, json={"text": "Hello, world."})
        return httpx.Response(404)

    result = await _client(handler).transcribe_url("http://cdn.example.com/audio.mp3")

    assert result.text == "Hello, world."
    assert result.words == []


async def test_enabled_reflects_base_url() -> None:
    assert _client(_noop, "http://x").enabled is True
    assert _client(_noop, "").enabled is False


async def test_not_configured_raises() -> None:
    client = _client(_noop, "")
    with pytest.raises(WhisperNotConfiguredError):
        await client.transcribe_url("http://cdn.example.com/a.mp3")


async def test_download_failure_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    with pytest.raises(WhisperError):
        await _client(handler).transcribe_url("http://cdn.example.com/a.mp3")


async def test_upstream_error_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/audio.mp3":
            return httpx.Response(200, content=b"x")
        return httpx.Response(400, json={"error": "bad request"})

    with pytest.raises(WhisperError):
        await _client(handler).transcribe_url("http://cdn.example.com/a.mp3")


async def test_malformed_response_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/audio.mp3":
            return httpx.Response(200, content=b"x")
        return httpx.Response(200, json={"text": 123})

    with pytest.raises(WhisperError):
        await _client(handler).transcribe_url("http://cdn.example.com/a.mp3")
