"""Shared test doubles and factories for backend tests."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx
from fastapi.testclient import TestClient

from app.services.deepgram import DeepgramNotConfiguredError, DeepgramTranscript
from app.services.llm import LLMNotConfiguredError

ClientFactory = Callable[..., TestClient]


class FakeLLM:
    """Configurable in-memory LLM provider for content tests."""

    def __init__(self, result: dict[str, Any] | None = None, *, enabled: bool = True) -> None:
        self._result = result or {}
        self._enabled = enabled
        self.calls: list[dict[str, Any]] = []

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def complete_json(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        self.calls.append(
            {"system": system, "user": user, "max_tokens": max_tokens, "temperature": temperature}
        )
        if not self._enabled:
            raise LLMNotConfiguredError("LLM API key is not configured")
        return self._result


class FakeDeepgram:
    """Configurable in-memory Deepgram provider for radio tests."""

    def __init__(
        self, transcript: DeepgramTranscript | None = None, *, enabled: bool = True
    ) -> None:
        self._transcript = transcript or DeepgramTranscript(text="", words=[])
        self._enabled = enabled
        self.calls: list[str] = []

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def transcribe_url(self, audio_url: str) -> DeepgramTranscript:
        self.calls.append(audio_url)
        if not self._enabled:
            raise DeepgramNotConfiguredError("Deepgram API key is not configured")
        return self._transcript


def build_rss(items: list[dict[str, Any]]) -> str:
    """Render a minimal RSS 2.0 document from a list of item dicts."""
    rendered = ""
    for item in items:
        enclosure = ""
        if item.get("audio_url"):
            enclosure = f'<enclosure url="{item["audio_url"]}" type="audio/mpeg" length="1"/>'
        rendered += (
            "<item>"
            f"<title>{item['title']}</title>"
            f"<link>{item.get('link', '')}</link>"
            f"<pubDate>{item.get('published', '')}</pubDate>"
            f"<description>{item.get('summary', '')}</description>"
            f"{enclosure}"
            "</item>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<rss version="2.0"><channel>'
        "<title>Test</title><link>https://example.com</link><description>d</description>"
        f"{rendered}</channel></rss>"
    )


def make_mock_http(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def chat_response(content: str) -> dict[str, Any]:
    """Build an OpenAI-compatible chat completion payload whose content is ``content``."""
    return {"choices": [{"message": {"content": content}}]}


def chat_error_response(status_code: int, code: str, message: str = "boom") -> httpx.Response:
    """Build an OpenAI-compatible *error* response (``chat_response`` can't).

    ``code`` is the upstream ``error.code`` a caller wants to exercise, e.g.
    Groq's ``json_validate_failed`` or any other value.
    """
    return httpx.Response(status_code, json={"error": {"code": code, "message": message}})
