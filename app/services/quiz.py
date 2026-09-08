"""Reading-comprehension quiz generator (multiple choice, via the LLM)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, ValidationError

from app.schemas.assist import QuizItem
from app.services.llm import LLMError, LLMProvider

_SYSTEM = (
    "You are a reading-comprehension quiz generator for an advanced English learner. "
    "Given a short text, write one multiple-choice question testing comprehension, "
    "with the correct answer and three plausible distractors. Respond ONLY with JSON: "
    '{"question": "string", "correct_answer": "string", '
    '"distractors": ["string", "string", "string"]}.'
)


class _QuizLLM(BaseModel):
    model_config = ConfigDict(extra="ignore")

    question: str
    correct_answer: str
    distractors: list[str]


class QuizService:
    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def generate(self, text: str) -> QuizItem:
        raw = await self._llm.complete_json(system=_SYSTEM, user=text, max_tokens=300)
        try:
            parsed = _QuizLLM.model_validate(raw)
        except ValidationError as exc:
            raise LLMError(f"Quiz validation failed: {exc}") from exc
        return QuizItem(
            question=parsed.question,
            correct_answer=parsed.correct_answer,
            distractors=parsed.distractors[:3],
        )
