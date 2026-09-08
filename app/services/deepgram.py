"""Typed client for Deepgram pre-recorded speech-to-text.

Used to transcribe a remote audio URL (a captured radio segment or podcast
episode). The client shares the process-wide ``httpx.AsyncClient`` and disables
cleanly when no API key is configured. Transient failures (5xx/429/transport)
are retried with bounded exponential backoff.
"""

from __future__ import annotations

import asyncio
import random
from typing import Any, Protocol

import httpx
from pydantic import BaseModel

from app.core.budget import SpendBudget

DEEPGRAM_BASE_URL = "https://api.deepgram.com/v1"


class DeepgramError(RuntimeError):
    """Raised when Deepgram request or response is unusable."""


class DeepgramNotConfiguredError(DeepgramError):
    """Raised when a transcription is attempted without a configured API key."""


class DeepgramBudgetExceeded(DeepgramError):
    """Raised when the daily Deepgram spend budget is exhausted."""


class DeepgramWord(BaseModel):
    word: str
    start: float
    end: float


class DeepgramTranscript(BaseModel):
    text: str
    words: list[DeepgramWord]


class DeepgramProvider(Protocol):
    """Interface implemented by ``DeepgramClient`` and test doubles."""

    @property
    def enabled(self) -> bool: ...

    async def transcribe_url(self, audio_url: str) -> DeepgramTranscript: ...


class DeepgramClient:
    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        api_key: str,
        model: str = "nova-2",
        max_retries: int = 2,
        timeout: float | None = None,
        budget: SpendBudget | None = None,
    ) -> None:
        self._client = client
        self._api_key = api_key
        self._model = model
        self._max_retries = max_retries
        self._timeout = timeout
        self._budget = budget

    @property
    def enabled(self) -> bool:
        return bool(self._api_key)

    async def transcribe_url(self, audio_url: str) -> DeepgramTranscript:
        if not self.enabled:
            raise DeepgramNotConfiguredError("Deepgram API key is not configured")
        if self._budget is not None and not self._budget.consume():
            raise DeepgramBudgetExceeded("Deepgram daily limit reached")

        url = f"{DEEPGRAM_BASE_URL}/listen"
        headers = {
            "Authorization": f"Token {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {"url": audio_url}
        params = {"model": self._model, "punctuate": "true"}

        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            if attempt > 0:
                backoff = min(4.0, 0.5 * (2 ** (attempt - 1)))
                await asyncio.sleep(backoff * random.uniform(0.5, 1.0))
            try:
                response = await self._client.post(
                    url, params=params, json=payload, headers=headers, timeout=self._timeout
                )
            except httpx.TransportError as exc:
                last_error = exc
                continue
            if response.status_code == 429 or response.status_code >= 500:
                last_error = DeepgramError(f"Deepgram upstream {response.status_code}")
                await response.aread()
                continue
            if response.status_code != 200:
                raise DeepgramError(
                    f"Deepgram request failed ({response.status_code}): {response.text[:200]}"
                )
            try:
                data = response.json()
            except ValueError as exc:
                raise DeepgramError("Deepgram returned a non-JSON response") from exc
            return _parse_transcript(data)

        raise DeepgramError(
            f"Deepgram request failed after {self._max_retries + 1} attempts: {last_error}"
        )


def _parse_transcript(data: Any) -> DeepgramTranscript:
    try:
        alternative = data["results"]["channels"][0]["alternatives"][0]
    except (KeyError, IndexError, TypeError) as exc:
        raise DeepgramError(f"Unexpected Deepgram response shape: {data!r}") from exc

    text = alternative.get("transcript", "")
    if not isinstance(text, str):
        raise DeepgramError(f"Deepgram transcript is not a string: {text!r}")

    words: list[DeepgramWord] = []
    for item in alternative.get("words", []) or []:
        if not isinstance(item, dict):
            continue
        word = item.get("word", "")
        start = item.get("start", 0.0)
        end = item.get("end", 0.0)
        if (
            isinstance(word, str)
            and isinstance(start, (int, float))
            and isinstance(end, (int, float))
        ):
            words.append(DeepgramWord(word=word, start=float(start), end=float(end)))

    return DeepgramTranscript(text=text, words=words)
