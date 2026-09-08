"""PREP drill endpoints: random scenario and evaluation."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.api.deps import rate_limited
from app.schemas.prep import PrepEvaluateRequest, PrepFeedback, PrepScenario
from app.services.prep import PrepService

router = APIRouter(prefix="/api/prep", tags=["prep"])


@router.get("/scenario", response_model=PrepScenario)
async def scenario(request: Request) -> PrepScenario:
    service: PrepService = request.app.state.prep
    return service.random_scenario()


@router.post(
    "/evaluate",
    response_model=PrepFeedback,
    dependencies=[Depends(rate_limited)],
)
async def evaluate(payload: PrepEvaluateRequest, request: Request) -> PrepFeedback:
    service: PrepService = request.app.state.prep
    return await service.evaluate(payload)
