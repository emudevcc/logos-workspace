"""Learning endpoints: curated verbs, pronunciation data, and grammar drills."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.api.deps import rate_limited
from app.schemas.learning import (
    ClozeDrill,
    DrillKind,
    GrammarCoachRequest,
    GrammarCoachResult,
    GrammarRule,
    IrregularVerb,
    MinimalPair,
    Pitfall,
    ShadowSentence,
    WordFormDrill,
)
from app.services.grammar_drill import GrammarDrillService
from app.services.grammar_rules import rule_for_date
from app.services.irregular_verbs import all_irregular_verbs
from app.services.minimal_pairs import MINIMAL_PAIRS, SPANISH_PITFALLS
from app.services.shadowing import ShadowingService

router = APIRouter(prefix="/api", tags=["learning"])


@router.get("/grammar/irregular-verbs", response_model=list[IrregularVerb])
async def irregular_verbs() -> list[IrregularVerb]:
    return all_irregular_verbs()


@router.get(
    "/grammar/drill",
    response_model=ClozeDrill,
    dependencies=[Depends(rate_limited)],
)
async def grammar_drill(
    kind: Annotated[DrillKind, Query()],
    request: Request,
) -> ClozeDrill:
    service: GrammarDrillService = request.app.state.grammar_drill
    return await service.drill(kind)


@router.get(
    "/grammar/word-forms",
    response_model=WordFormDrill,
    dependencies=[Depends(rate_limited)],
)
async def grammar_word_forms(request: Request) -> WordFormDrill:
    service: GrammarDrillService = request.app.state.grammar_drill
    return await service.word_forms()


@router.get("/grammar/rule-of-day", response_model=GrammarRule)
async def grammar_rule_of_day(
    day: Annotated[date | None, Query(alias="date")] = None,
) -> GrammarRule:
    return rule_for_date(day or date.today())


@router.post(
    "/grammar/coach",
    response_model=GrammarCoachResult,
    dependencies=[Depends(rate_limited)],
)
async def grammar_coach(payload: GrammarCoachRequest, request: Request) -> GrammarCoachResult:
    service: GrammarDrillService = request.app.state.grammar_drill
    return await service.coach(payload.question)


@router.get("/pronunciation/minimal-pairs", response_model=list[MinimalPair])
async def minimal_pairs() -> list[MinimalPair]:
    return list(MINIMAL_PAIRS)


@router.get("/pronunciation/pitfalls", response_model=list[Pitfall])
async def pitfalls() -> list[Pitfall]:
    return list(SPANISH_PITFALLS)


@router.get(
    "/pronunciation/sentence",
    response_model=ShadowSentence,
    dependencies=[Depends(rate_limited)],
)
async def pronunciation_sentence(request: Request) -> ShadowSentence:
    service: ShadowingService = request.app.state.shadowing
    return ShadowSentence(sentence=await service.random_sentence())
