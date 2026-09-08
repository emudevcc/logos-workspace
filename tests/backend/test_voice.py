"""Unit tests for the voice roleplay service."""

import pytest

from app.schemas.assist import Turn, VoiceTurnRequest
from app.services.llm import LLMNotConfiguredError
from app.services.voice import VoiceService
from tests.backend.helpers import FakeLLM


async def test_turn_returns_partner_response() -> None:
    llm = FakeLLM(
        result={
            "partner_says": "Can you clarify the timeline?",
            "follow_up_hint": "Ask for specifics.",
        }
    )
    service = VoiceService(llm)
    result = await service.turn(VoiceTurnRequest(scenario="s", user_says="u"))
    assert result.partner_says == "Can you clarify the timeline?"


async def test_turn_not_configured_raises() -> None:
    service = VoiceService(FakeLLM(enabled=False))
    with pytest.raises(LLMNotConfiguredError):
        await service.turn(VoiceTurnRequest(scenario="s", user_says="u"))


async def test_turn_caps_history_to_last_ten() -> None:
    llm = FakeLLM(result={"partner_says": "ok", "follow_up_hint": ""})
    service = VoiceService(llm)
    history = [Turn(role="user", text=f"turn-{i}") for i in range(15)]
    await service.turn(VoiceTurnRequest(scenario="s", user_says="hello", history=history))
    prompt = llm.calls[0]["user"]
    assert "turn-0" not in prompt
    assert "turn-14" in prompt
