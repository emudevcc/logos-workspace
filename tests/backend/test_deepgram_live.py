"""Tests for the Deepgram live streaming session."""

import asyncio
import json
from typing import Any

import websockets

from app.services.deepgram_live import DeepgramLiveSession, parse_results_message


def test_parse_results_message_extracts_transcript() -> None:
    message = {
        "type": "Results",
        "channel": {"alternatives": [{"transcript": "hello world"}]},
        "is_final": True,
    }
    assert parse_results_message(message) == ("hello world", True)


def test_parse_results_message_ignores_non_results() -> None:
    assert parse_results_message({"type": "Metadata"}) is None
    assert parse_results_message("not a dict") is None
    assert parse_results_message({"type": "Results", "channel": {"alternatives": []}}) is None
    assert (
        parse_results_message(
            {"type": "Results", "channel": {"alternatives": [{"transcript": ""}]}}
        )
        is None
    )


async def test_live_session_receives_transcript() -> None:
    events: list[tuple[str, bool]] = []

    async def handler(ws: Any) -> None:
        async for _raw in ws:
            await ws.send(
                json.dumps(
                    {
                        "type": "Results",
                        "channel": {"alternatives": [{"transcript": "hello world"}]},
                        "is_final": True,
                    }
                )
            )
            break

    async with websockets.serve(handler, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        session = DeepgramLiveSession(api_key="k", base_uri=f"ws://127.0.0.1:{port}/listen")

        async def on_transcript(text: str, is_final: bool) -> None:
            events.append((text, is_final))

        await session.connect(16000, on_transcript)
        await session.send_audio(b"\x00\x01\x02\x03")
        for _ in range(100):
            if events:
                break
            await asyncio.sleep(0.01)
        await session.close()

    assert events == [("hello world", True)]
