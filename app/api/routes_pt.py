"""Português cockpit endpoints: PT-BR word of day, news, grammar, pronunciation."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.api.deps import rate_limited
from app.schemas.pt import (
    PtGrammarCoachRequest,
    PtGrammarCoachResult,
    PtGrammarRule,
    PtMinimalPair,
    PtNewsPulse,
    PtPitfall,
    PtSentence,
    PtWordOfDay,
)
from app.services.pt_content import (
    MINIMAL_PAIRS_PT,
    PITFALLS_PT,
    all_rules,
    random_rule,
    random_word,
    rule_for_date,
    word_for_date,
)
from app.services.pt_generators import PtGrammarCoach, PtPracticeSentence
from app.services.pt_news import PtNewsService

router = APIRouter(prefix="/api/pt", tags=["pt"])


@router.get("/word-of-day", response_model=PtWordOfDay)
async def word_of_day(
    day: Annotated[date | None, Query(alias="date")] = None,
) -> PtWordOfDay:
    return word_for_date(day or date.today())


@router.get("/word-of-day/random", response_model=PtWordOfDay)
async def word_of_day_random() -> PtWordOfDay:
    """A curated PT-BR word that avoids recently served items."""
    return random_word()


@router.get("/news", response_model=PtNewsPulse)
async def news_pulse(
    request: Request,
    refresh: bool = Query(default=False),
) -> PtNewsPulse:
    service: PtNewsService = request.app.state.pt_news
    return await service.pulse(refresh=refresh)


@router.get("/grammar/rules", response_model=list[PtGrammarRule])
async def grammar_rules() -> list[PtGrammarRule]:
    return all_rules()


@router.get("/grammar/rule-of-day", response_model=PtGrammarRule)
async def grammar_rule_of_day(
    day: Annotated[date | None, Query(alias="date")] = None,
) -> PtGrammarRule:
    return rule_for_date(day or date.today())


@router.get("/grammar/rule-random", response_model=PtGrammarRule)
async def grammar_rule_random(
    exclude: Annotated[str | None, Query(max_length=200)] = None,
) -> PtGrammarRule:
    """A random rule different from the currently shown one ('Outra regra')."""
    return random_rule(exclude_title=exclude)


@router.post(
    "/grammar/coach",
    response_model=PtGrammarCoachResult,
    dependencies=[Depends(rate_limited)],
)
async def grammar_coach(
    payload: PtGrammarCoachRequest,
    request: Request,
) -> PtGrammarCoachResult:
    service: PtGrammarCoach = request.app.state.pt_coach
    return await service.answer(payload.pergunta)


@router.get("/pronunciation/minimal-pairs", response_model=list[PtMinimalPair])
async def minimal_pairs() -> list[PtMinimalPair]:
    return list(MINIMAL_PAIRS_PT)


@router.get("/pronunciation/pitfalls", response_model=list[PtPitfall])
async def pitfalls() -> list[PtPitfall]:
    return list(PITFALLS_PT)


@router.get(
    "/practice/sentence",
    response_model=PtSentence,
    dependencies=[Depends(rate_limited)],
)
async def practice_sentence(request: Request) -> PtSentence:
    service: PtPracticeSentence = request.app.state.pt_sentence
    return await service.sentence()
