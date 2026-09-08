"""Voice conversational partner: structured roleplay turns via the LLM."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, ValidationError

from app.schemas.assist import VoiceTurnRequest, VoiceTurnResponse
from app.services.llm import LLMError, LLMProvider

_SYSTEM = (
    "You are a native-English-speaking roleplay partner in a workplace scenario. Stay in "
    "character as the other party. Reply naturally in 1-3 sentences, then give the learner "
    "a short follow-up hint. Respond ONLY with JSON shaped exactly like: "
    '{"partner_says": "string", "follow_up_hint": "string"}.'
)


class _VoiceLLM(BaseModel):
    model_config = ConfigDict(extra="ignore")

    partner_says: str
    follow_up_hint: str = ""


class VoiceService:
    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def turn(self, request: VoiceTurnRequest) -> VoiceTurnResponse:
        recent = request.history[-10:]
        history = "\n".join(f"{turn.role}: {turn.text}" for turn in recent)
        user = (
            f"Scenario: {request.scenario}\n\n"
            f"Conversation so far:\n{history}\n"
            f"User: {request.user_says}"
        )
        raw = await self._llm.complete_json(system=_SYSTEM, user=user, max_tokens=400)
        try:
            parsed = _VoiceLLM.model_validate(raw)
        except ValidationError as exc:
            raise LLMError(f"Voice turn validation failed: {exc}") from exc
        return VoiceTurnResponse(
            partner_says=parsed.partner_says,
            follow_up_hint=parsed.follow_up_hint,
        )
