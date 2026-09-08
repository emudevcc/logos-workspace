"""Unit tests for the PREP drill service."""

from typing import Any

import pytest

from app.schemas.prep import PrepEvaluateRequest
from app.services.llm import LLMError, LLMNotConfiguredError
from app.services.prep import SCENARIOS, PrepService
from tests.backend.helpers import FakeLLM


def _feedback(**overrides: object) -> dict[str, Any]:
    base: dict[str, Any] = {
        "conciseness_score": 80,
        "conciseness_feedback": "tight",
        "structure_score": 75,
        "structure_feedback": "clear PREP",
        "bluf_rewrite": "Bottom line first.",
        "overall_feedback": "good",
    }
    base.update(overrides)
    return base


def test_scenarios_are_valid() -> None:
    assert SCENARIOS
    for scenario in SCENARIOS:
        assert scenario.id
        assert scenario.context
        assert scenario.task


def test_random_scenario_is_a_member() -> None:
    service = PrepService(FakeLLM())
    assert service.random_scenario() in SCENARIOS


async def test_evaluate_returns_feedback() -> None:
    service = PrepService(FakeLLM(result=_feedback()))
    result = await service.evaluate(PrepEvaluateRequest(scenario="s", response="r"))
    assert result.conciseness_score == 80
    assert result.bluf_rewrite == "Bottom line first."


async def test_evaluate_clamps_scores() -> None:
    service = PrepService(FakeLLM(result=_feedback(conciseness_score=500, structure_score=-10)))
    result = await service.evaluate(PrepEvaluateRequest(scenario="s", response="r"))
    assert result.conciseness_score == 100
    assert result.structure_score == 0


async def test_evaluate_not_configured_raises() -> None:
    service = PrepService(FakeLLM(enabled=False))
    with pytest.raises(LLMNotConfiguredError):
        await service.evaluate(PrepEvaluateRequest(scenario="s", response="r"))


async def test_evaluate_malformed_raises() -> None:
    service = PrepService(FakeLLM(result={"bad": "shape"}))
    with pytest.raises(LLMError):
        await service.evaluate(PrepEvaluateRequest(scenario="s", response="r"))


def test_random_scenario_avoids_recent_repeats() -> None:
    service = PrepService(FakeLLM())
    seen_ids = []
    # SCENARIOS has several members: successive draws must differ while the
    # recent window (< pool size) still has room.
    for _ in range(min(3, len(SCENARIOS))):
        picked = service.random_scenario()
        assert picked.id not in seen_ids
        seen_ids.append(picked.id)
