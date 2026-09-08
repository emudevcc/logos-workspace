"""Speaking monologue drill: curated topics + LLM evaluation of a recording."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.schemas.assist import MonologueFeedback
from app.services.llm import LLMError, LLMProvider

TOPICS: tuple[str, ...] = (
    "Describe a project you led and what you learned from it.",
    "Explain a time you had to push back on a request at work.",
    "Argue for remote work or for returning to the office.",
    "Explain a technical concept to a non-technical colleague.",
    "Describe the most useful feedback you have ever received.",
    "Tell the story of a deadline you almost missed.",
    "Make the case for investing in a product you believe in.",
    "Explain how you would onboard a new team member.",
)

_EVAL_SYSTEM = (
    "You are an executive speaking coach evaluating an English monologue from a "
    "Spanish-speaking learner at B2→C1. Score structure, fluency, vocabulary, and "
    "grammar from 0 to 100. List up to three strengths, up to three specific "
    "improvements, and provide a strong model answer for the same topic. Respond ONLY "
    'with JSON shaped exactly like: {"structure_score": int, "fluency_score": int, '
    '"vocabulary_score": int, "grammar_score": int, "strengths": ["string"], '
    '"improvements": ["string"], "model_answer": "string"}.'
)


class _FeedbackLLM(BaseModel):
    model_config = ConfigDict(extra="ignore")

    structure_score: int
    fluency_score: int
    vocabulary_score: int
    grammar_score: int
    strengths: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    model_answer: str = ""


class MonologueService:
    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    def topics(self) -> list[str]:
        return list(TOPICS)

    async def evaluate(
        self, topic: str, transcript: str, duration_seconds: float
    ) -> MonologueFeedback:
        user = f"Topic: {topic}\nDuration: {duration_seconds:.0f}s\nTranscript:\n{transcript}"
        raw = await self._llm.complete_json(system=_EVAL_SYSTEM, user=user, max_tokens=800)
        try:
            parsed = _FeedbackLLM.model_validate(raw)
        except ValidationError as exc:
            raise LLMError(f"Monologue feedback validation failed: {exc}") from exc
        return MonologueFeedback(
            structure_score=_clamp(parsed.structure_score),
            fluency_score=_clamp(parsed.fluency_score),
            vocabulary_score=_clamp(parsed.vocabulary_score),
            grammar_score=_clamp(parsed.grammar_score),
            strengths=parsed.strengths[:3],
            improvements=parsed.improvements[:3],
            model_answer=parsed.model_answer,
        )


def _clamp(score: int) -> int:
    return max(0, min(100, score))
