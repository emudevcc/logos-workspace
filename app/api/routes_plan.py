"""Weekly study-plan endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.api.deps import rate_limited
from app.schemas.plan import WeeklyPlanRequest, WeeklyPlanResult
from app.services.plan import WeeklyPlanService

router = APIRouter(prefix="/api/plan", tags=["plan"])


@router.post(
    "/weekly",
    response_model=WeeklyPlanResult,
    dependencies=[Depends(rate_limited)],
)
async def weekly_plan(payload: WeeklyPlanRequest, request: Request) -> WeeklyPlanResult:
    service: WeeklyPlanService = request.app.state.plan
    return await service.generate(payload)
