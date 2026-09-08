"""Live radio transcription relay: browser audio -> Deepgram -> dashboard.

The browser sends 16-bit PCM as raw binary WebSocket frames (low latency, no
base64/JSON overhead); control messages ("start"/"stop") are JSON text frames.
"""

from __future__ import annotations

import json
import logging
from contextlib import suppress
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.ws_manager import ConnectionManager
from app.services.deepgram_live import DeepgramLiveError, DeepgramLiveSession

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/radio")
async def radio_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    settings = websocket.app.state.settings
    manager: ConnectionManager = websocket.app.state.ws_manager

    if not settings.deepgram_api_key:
        await websocket.send_json({"type": "error", "detail": "Deepgram is not configured"})
        await websocket.close()
        return

    session: DeepgramLiveSession | None = None
    chunk_count = 0

    async def on_transcript(text: str, is_final: bool) -> None:
        await manager.broadcast({"type": "radio:transcript", "text": text, "final": is_final})

    try:
        while True:
            event = await websocket.receive()
            if event["type"] == "websocket.disconnect":
                break
            if event["type"] != "websocket.receive":
                continue

            if event.get("text") is not None:
                message = _parse(event["text"])
                if message is None:
                    continue
                msg_type = message.get("type")
                if msg_type == "start" and session is None:
                    sample_rate = int(message.get("sample_rate", 48000))
                    session = DeepgramLiveSession(
                        api_key=settings.deepgram_api_key,
                        model=settings.deepgram_model,
                    )
                    await session.connect(sample_rate, on_transcript)
                    logger.info("live STT started (sample_rate=%d)", sample_rate)
                elif msg_type == "stop":
                    logger.info("live STT stopped (%d audio chunks)", chunk_count)
                    break
            elif event.get("bytes") is not None:
                if session is not None:
                    await session.send_audio(event["bytes"])
                    chunk_count += 1
    except WebSocketDisconnect:
        pass
    except DeepgramLiveError as exc:
        logger.error("live STT failed: %s", exc)
        with suppress(Exception):
            await websocket.send_json({"type": "error", "detail": str(exc)})
    finally:
        if session is not None:
            await session.close()


def _parse(raw: str) -> dict[str, Any] | None:
    try:
        message = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return message if isinstance(message, dict) else None
