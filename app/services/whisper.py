"""Typed client for a local whisper.cpp speech-to-text server.

Replaces Deepgram for pre-recorded audio when ``STT_PROVIDER=whisper``. The client
downloads the audio itself with the shared ``httpx.AsyncClient`` and posts it to the
whisper.cpp ``/inference`` endpoint. It satisfies the same ``DeepgramProvider``
protocol, so call sites (``RadioService``) are unchanged.
"""

from __future__ import annotations

import asyncio
import random
from typing import Any
from urllib.parse import urlparse

import httpx

from app.services.deepgram import DeepgramTranscript


class WhisperError(RuntimeError):
    """Raised when a local Whisper request or response is unusable."""


class WhisperNotConfiguredError(WhisperError):
    """Raised when transcription is attempted without a configured base URL."""


class WhisperClient:
    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        base_url: str,
        max_retries: int = 2,
        timeout: float | None = None,
    ) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._max_retries = max_retries
        self._timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(self._base_url)

    async def transcribe_url(self, audio_url: str) -> DeepgramTranscript:
        if not self.enabled:
            raise WhisperNotConfiguredError("Whisper base URL is not configured")
        audio = await self._download(audio_url)
        text = await self._transcribe(audio, audio_url)
        return DeepgramTranscript(text=text, words=[])

    async def _download(self, audio_url: str) -> bytes:
        headers = {"User-Agent": "EnglishCockpitOS/1.0"}
        try:
            response = await self._client.get(audio_url, headers=headers, timeout=self._timeout)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise WhisperError(f"Failed to download audio from {audio_url}: {exc}") from exc
        return response.content

    async def _transcribe(self, audio: bytes, audio_url: str) -> str:
        url = f"{self._base_url}/inference"
        filename = _filename_from_url(audio_url)
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            if attempt > 0:
                backoff = min(4.0, 0.5 * (2 ** (attempt - 1)))
                await asyncio.sleep(backoff * random.uniform(0.5, 1.0))
            try:
                response = await self._client.post(
                    url,
                    files={"file": (filename, audio, "application/octet-stream")},
                    timeout=self._timeout,
                )
            except httpx.TransportError as exc:
                last_error = exc
                continue
            if response.status_code >= 500:
                last_error = WhisperError(f"Whisper upstream {response.status_code}")
                await response.aread()
                continue
            if response.status_code != 200:
                raise WhisperError(
                    f"Whisper request failed ({response.status_code}): {response.text[:200]}"
                )
            try:
                data = response.json()
            except ValueError as exc:
                raise WhisperError("Whisper returned a non-JSON response") from exc
            return _parse_text(data)
        raise WhisperError(
            f"Whisper request failed after {self._max_retries + 1} attempts: {last_error}"
        )


def _parse_text(data: Any) -> str:
    if not isinstance(data, dict):
        raise WhisperError(f"Unexpected Whisper response shape: {data!r}")
    text = data.get("text", "")
    if not isinstance(text, str):
        raise WhisperError(f"Whisper transcript is not a string: {text!r}")
    return text


def _filename_from_url(audio_url: str) -> str:
    path = urlparse(audio_url).path
    name = path.rsplit("/", 1)[-1] if path else ""
    return name or "audio"
