"""Writing Coach: grammar/usage correction of a draft via the LLM."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.schemas.assist import Correction, CorrectResult
from app.services.llm import LLMError, LLMProvider

_SYSTEM = (
    "You are an English writing coach for a Spanish-speaking learner at B2→C1. Correct "
    "the grammar, usage, punctuation, and word-choice errors in the draft while preserving "
    "its meaning, tone, and length. Return the fully corrected text and a list of specific "
    "corrections (what was wrong, how to fix it, and a one-line explanation). If the text "
    "is already correct, return an empty corrections list. Respond ONLY with JSON shaped "
    'exactly like: {"corrected": "string", "corrections": [{"original": "string", '
    '"corrected": "string", "explanation": "string"}]}.'
)


class _CorrectionLLM(BaseModel):
    model_config = ConfigDict(extra="ignore")

    original: str
    corrected: str
    explanation: str = ""


class _CorrectLLM(BaseModel):
    model_config = ConfigDict(extra="ignore")

    corrected: str
    corrections: list[_CorrectionLLM] = Field(default_factory=list)


class WritingCoachService:
    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def correct(self, draft: str) -> CorrectResult:
        raw = await self._llm.complete_json(system=_SYSTEM, user=draft, max_tokens=800)
        try:
            parsed = _CorrectLLM.model_validate(raw)
        except ValidationError as exc:
            raise LLMError(f"Writing-correct validation failed: {exc}") from exc
        corrections = [
            Correction(
                original=item.original,
                corrected=item.corrected,
                explanation=item.explanation,
            )
            for item in parsed.corrections
        ]
        return CorrectResult(
            corrected=parsed.corrected,
            corrections=corrections,
            error_count=len(corrections),
        )
