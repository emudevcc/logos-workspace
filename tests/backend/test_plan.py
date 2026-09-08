"""Tests for the weekly-plan service."""

import pytest

from app.schemas.plan import WeeklyPlanRequest
from app.services.llm import LLMError, LLMNotConfiguredError
from app.services.plan import WeeklyPlanService
from tests.backend.helpers import FakeLLM


async def test_generate_orders_days_canonically() -> None:
    llm = FakeLLM(
        result={
            "days": [
                {"day": "Friday", "activity": "Listen", "duration_minutes": 20},
                {"day": "Monday", "activity": "Speak", "duration_minutes": 30},
            ],
            "tip": "Stay consistent.",
        }
    )
    result = await WeeklyPlanService(llm).generate(
        WeeklyPlanRequest(goal="fluency", minutes_per_day=30, focus_areas=["Speaking"])
    )
    assert [day.day for day in result.days] == ["Monday", "Friday"]
    assert result.tip == "Stay consistent."


async def test_generate_ignores_unknown_days() -> None:
    llm = FakeLLM(
        result={
            "days": [
                {"day": "Funday", "activity": "X", "duration_minutes": 10},
                {"day": "Tuesday", "activity": "Y", "duration_minutes": 10},
            ],
            "tip": "",
        }
    )
    result = await WeeklyPlanService(llm).generate(WeeklyPlanRequest(goal="g"))
    assert [day.day for day in result.days] == ["Tuesday"]


async def test_generate_not_configured_raises() -> None:
    service = WeeklyPlanService(FakeLLM(enabled=False))
    with pytest.raises(LLMNotConfiguredError):
        await service.generate(WeeklyPlanRequest(goal="g"))


async def test_generate_malformed_raises() -> None:
    service = WeeklyPlanService(FakeLLM(result={"days": "nope"}))
    with pytest.raises(LLMError):
        await service.generate(WeeklyPlanRequest(goal="g"))
