"""Models for the weekly study-plan endpoint."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class WeeklyPlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal: str = Field(min_length=1, max_length=1000)
    minutes_per_day: int = Field(default=30, ge=5, le=240)
    focus_areas: list[str] = Field(default_factory=list)


class PlanDay(BaseModel):
    day: str
    activity: str
    duration_minutes: int = Field(default=0, ge=0)


class WeeklyPlanResult(BaseModel):
    days: list[PlanDay]
    tip: str = ""
