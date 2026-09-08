"""Deepgram live (streaming) speech-to-text session over WebSocket.

The browser captures the playing radio stream, resamples it via the Web Audio
API, and forwards 16-bit PCM frames to this backend, which relays them to
Deepgram's live endpoint and reports transcripts back.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from contextlib import suppress
from typing import Any

import websockets

DEEPGRAM_LIVE_URI = "wss://api.deepgram.com/v1/listen"

TranscriptCallback = Callable[[str, bool], Awaitable[None]]


class DeepgramLiveError(RuntimeError):
    """Raised when the live session cannot be established or runs into trouble."""


def parse_results_message(message: Any) -> tuple[str, bool] | None:
    """Extract ``(transcript, is_final)`` from a Deepgram live message, if any."""
    if not isinstance(message, dict) or message.get("type") != "Results":
        return None
    channel = message.get("channel")
    if not isinstance(channel, dict):
        return None
    alternatives = channel.get("alternatives")
    if not isinstance(alternatives, list) or not alternatives:
        return None
    first = alternatives[0]
    if not isinstance(first, dict):
        return None
    transcript = first.get("transcript", "")
    if not isinstance(transcript, str) or not transcript.strip():
        return None
    return transcript, bool(message.get("is_final"))


class DeepgramLiveSession:
    def __init__(
        self, *, api_key: str, model: str = "nova-2", base_uri: str = DEEPGRAM_LIVE_URI
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_uri = base_uri
        self._ws: Any = None
        self._receiver: asyncio.Task[None] | None = None

    async def connect(self, sample_rate: int, on_transcript: TranscriptCallback) -> None:
        params = (
            f"model={self._model}&encoding=linear16&sample_rate={sample_rate}"
            "&channels=1&interim_results=true&punctuate=true"
        )
        uri = f"{self._base_uri}?{params}"
        try:
            self._ws = await websockets.connect(
                uri, additional_headers={"Authorization": f"Token {self._api_key}"}
            )
        except Exception as exc:
            raise DeepgramLiveError(f"Deepgram live connect failed: {exc}") from exc
        self._receiver = asyncio.create_task(self._receive(on_transcript))

    async def send_audio(self, chunk: bytes) -> None:
        if self._ws is None:
            raise DeepgramLiveError("session is not connected")
        await self._ws.send(chunk)

    async def _receive(self, on_transcript: TranscriptCallback) -> None:
        assert self._ws is not None
        async for raw in self._ws:
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                continue
            parsed = parse_results_message(message)
            if parsed is not None:
                transcript, is_final = parsed
                await on_transcript(transcript, is_final)

    async def close(self) -> None:
        if self._receiver is not None:
            self._receiver.cancel()
            with suppress(asyncio.CancelledError):
                await self._receiver
            self._receiver = None
        if self._ws is not None:
            with suppress(Exception):
                await self._ws.send(json.dumps({"type": "CloseStream"}))
            await self._ws.close()
            self._ws = None
