"""Rapid-Fire PREP drill: random scenarios and LLM evaluation."""

from __future__ import annotations

import random
from collections import deque

from pydantic import BaseModel, ConfigDict, ValidationError

from app.schemas.prep import PrepEvaluateRequest, PrepFeedback, PrepScenario
from app.services.llm import LLMError, LLMProvider

_SCENARIO_WINDOW = 3

SCENARIOS: tuple[PrepScenario, ...] = (
    PrepScenario(
        id="system_incident",
        context="The payment service is returning 5xx errors during peak traffic.",
        task="As the on-call engineer, tell the incident channel how you will respond, "
        "using PREP (Point, Reason, Evidence, Point).",
    ),
    PrepScenario(
        id="scope_creep",
        context="A stakeholder keeps adding requirements in the middle of the sprint.",
        task="Push back professionally in the stakeholder meeting using PREP.",
    ),
    PrepScenario(
        id="design_debate",
        context="The team is split between two competing architecture options.",
        task="Argue for your preferred option using PREP.",
    ),
    PrepScenario(
        id="client_qna",
        context="A client asks why the project is running behind the agreed schedule.",
        task="Answer the client concisely using PREP.",
    ),
    PrepScenario(
        id="deadline_pushback",
        context="Your manager asks you to commit to an impossible deadline.",
        task="Respond to your manager using PREP.",
    ),
    PrepScenario(
        id="budget_reduction",
        context="Leadership proposes cutting your team's budget by 20%.",
        task="Make the case against the cut using PREP.",
    ),
)

_EVAL_SYSTEM = (
    "You are an executive communication coach. Evaluate a PREP (Point, Reason, Evidence, "
    "Point) response. Score conciseness and structure from 0 to 100, give concise feedback "
    "for each, and provide a native BLUF (Bottom-Line Up Front) rewrite. Respond ONLY with "
    'JSON shaped exactly like: {"conciseness_score": int, "conciseness_feedback": "string", '
    '"structure_score": int, "structure_feedback": "string", "bluf_rewrite": "string", '
    '"overall_feedback": "string"}.'
)


class _LLMEval(BaseModel):
    model_config = ConfigDict(extra="ignore")

    conciseness_score: int
    conciseness_feedback: str
    structure_score: int
    structure_feedback: str
    bluf_rewrite: str
    overall_feedback: str


class PrepService:
    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm
        self._recent: deque[PrepScenario] = deque(maxlen=_SCENARIO_WINDOW)

    def scenarios(self) -> tuple[PrepScenario, ...]:
        return SCENARIOS

    def random_scenario(self) -> PrepScenario:
        """Return a scenario, avoiding any served by a recent call (no repeats).

        Falls back to the full pool when almost every scenario is in the recent
        window, so a reload or refresh never re-serves the same prompt while
        unseen ones remain.
        """
        recent = {scenario.id for scenario in self._recent}
        candidates = [scenario for scenario in SCENARIOS if scenario.id not in recent]
        if not candidates:
            candidates = list(SCENARIOS)
        scenario = random.choice(candidates)
        self._recent.append(scenario)
        return scenario

    async def evaluate(self, request: PrepEvaluateRequest) -> PrepFeedback:
        user = (
            f"Scenario: {request.scenario}\n\n"
            f"Response ({request.elapsed_seconds}s):\n{request.response}"
        )
        raw = await self._llm.complete_json(system=_EVAL_SYSTEM, user=user, max_tokens=600)
        try:
            parsed = _LLMEval.model_validate(raw)
        except ValidationError as exc:
            raise LLMError(f"PREP feedback validation failed: {exc}") from exc

        return PrepFeedback(
            conciseness_score=_clamp(parsed.conciseness_score),
            conciseness_feedback=parsed.conciseness_feedback,
            structure_score=_clamp(parsed.structure_score),
            structure_feedback=parsed.structure_feedback,
            bluf_rewrite=parsed.bluf_rewrite,
            overall_feedback=parsed.overall_feedback,
        )


def _clamp(score: int) -> int:
    return max(0, min(100, score))
