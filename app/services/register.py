"""Register-swap exercise: rewrite a sentence in a target register via the LLM."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, ValidationError

from app.schemas.assist import RegisterResult
from app.services.llm import LLMError, LLMProvider

_SYSTEM = (
    "You are an English register coach. Rewrite the given sentence in the requested "
    "register while preserving meaning. Respond ONLY with JSON: "
    '{"rewritten": "string"}.'
)


class _RegisterLLM(BaseModel):
    model_config = ConfigDict(extra="ignore")

    rewritten: str


class RegisterService:
    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def rewrite(self, text: str, register: str) -> RegisterResult:
        raw = await self._llm.complete_json(
            system=_SYSTEM, user=f"Register: {register}\nText: {text}", max_tokens=300
        )
        try:
            parsed = _RegisterLLM.model_validate(raw)
        except ValidationError as exc:
            raise LLMError(f"Register validation failed: {exc}") from exc
        return RegisterResult(rewritten=parsed.rewritten)
