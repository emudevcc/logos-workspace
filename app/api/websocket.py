"""``/ws`` endpoint: per-connection receive loop and heartbeat responder."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.ws_manager import ConnectionLimitError, ConnectionManager

router = APIRouter()

MAX_FRAME_SIZE = 64 * 1024


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    manager: ConnectionManager = websocket.app.state.ws_manager
    try:
        await manager.connect(websocket)
    except ConnectionLimitError:
        return
    try:
        while True:
            raw = await websocket.receive_text()
            if len(raw) > MAX_FRAME_SIZE:
                await websocket.close(code=1009)
                return
            message = _parse_message(raw)
            if message is None:
                continue
            if message.get("type") == "pong":
                manager.touch(websocket)
            elif message.get("type") == "ping":
                await manager.send_json(websocket, {"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)


def _parse_message(raw: str) -> dict[str, Any] | None:
    try:
        message = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return message if isinstance(message, dict) else None
