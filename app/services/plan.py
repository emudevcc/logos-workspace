"""Weekly study-plan generator via the LLM."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.schemas.plan import PlanDay, WeeklyPlanRequest, WeeklyPlanResult
from app.services.llm import LLMError, LLMProvider

_DAYS: tuple[str, ...] = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)

_SYSTEM = (
    "You are an English learning coach for a Spanish-speaking professional at B2→C1. "
    "Build a personalized seven-day study plan (Monday through Sunday) from the learner's "
    "goal, available minutes per day, and focus areas. Each day must include one concrete "
    "activity and its duration in minutes (which may be 0 for a rest day). End with one "
    "motivational tip. Respond ONLY with JSON shaped exactly like: "
    '{"days": [{"day": "Monday", "activity": "string", "duration_minutes": int}, ...], '
    '"tip": "string"}.'
)


class _PlanDayLLM(BaseModel):
    model_config = ConfigDict(extra="ignore")

    day: str
    activity: str
    duration_minutes: int = Field(default=0, ge=0)


class _PlanLLM(BaseModel):
    model_config = ConfigDict(extra="ignore")

    days: list[_PlanDayLLM] = Field(default_factory=list)
    tip: str = ""


class WeeklyPlanService:
    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def generate(self, request: WeeklyPlanRequest) -> WeeklyPlanResult:
        focus = ", ".join(request.focus_areas) or "all core skills"
        user = (
            f"Goal: {request.goal}\n"
            f"Minutes per day: {request.minutes_per_day}\n"
            f"Focus areas: {focus}"
        )
        raw = await self._llm.complete_json(system=_SYSTEM, user=user, max_tokens=800)
        try:
            parsed = _PlanLLM.model_validate(raw)
        except ValidationError as exc:
            raise LLMError(f"Weekly plan validation failed: {exc}") from exc

        days = _order_days(parsed.days)
        return WeeklyPlanResult(
            days=[
                PlanDay(
                    day=item.day,
                    activity=item.activity,
                    duration_minutes=item.duration_minutes,
                )
                for item in days
            ],
            tip=parsed.tip,
        )


def _order_days(days: list[_PlanDayLLM]) -> list[_PlanDayLLM]:
    by_day = {item.day.strip().lower(): item for item in days}
    ordered: list[_PlanDayLLM] = []
    for canonical in _DAYS:
        item = by_day.get(canonical.lower())
        if item is not None:
            ordered.append(
                _PlanDayLLM(
                    day=canonical,
                    activity=item.activity,
                    duration_minutes=item.duration_minutes,
                )
            )
    return ordered
