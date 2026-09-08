"""Content endpoints: Word-of-Day, News, Podcast, and dictionary lookup."""

from __future__ import annotations

import logging
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, Request

from app.schemas.content import (
    DictionaryLookup,
    NewsPulse,
    PodcastDigest,
    WordEntry,
    WordOfDay,
)
from app.services.dictionary import DictionaryService
from app.services.llm import LLMError
from app.services.news import NewsService
from app.services.podcast import PodcastService
from app.services.word_of_day import WordOfDayGenerator, entry_for_date, list_entries, random_entry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["content"])


@router.get("/word-of-day", response_model=WordOfDay)
async def word_of_day(
    day: Annotated[date | None, Query(alias="date")] = None,
) -> WordOfDay:
    return entry_for_date(day or date.today())


@router.get("/word-of-day/entries", response_model=list[WordEntry])
async def word_of_day_entries() -> list[WordEntry]:
    return list_entries()


@router.get("/word-of-day/random", response_model=WordOfDay)
async def word_of_day_random(request: Request) -> WordOfDay:
    """A fresh item: LLM-generated on the fly when available, else curated."""
    generator = getattr(request.app.state, "word_of_day", None)
    if isinstance(generator, WordOfDayGenerator) and generator.enabled:
        try:
            return await generator.generate()
        except LLMError as exc:
            logger.warning("Word-of-day generation failed, falling back: %s", exc)
    return random_entry()


@router.get("/news", response_model=NewsPulse)
async def news_pulse(
    request: Request,
    refresh: bool = Query(default=False),
) -> NewsPulse:
    service: NewsService = request.app.state.news
    return await service.pulse(refresh=refresh)


@router.get("/podcast-digest", response_model=PodcastDigest)
async def podcast_digest(
    request: Request,
    refresh: bool = Query(default=False),
) -> PodcastDigest:
    service: PodcastService = request.app.state.podcast
    return await service.digest(refresh=refresh)


@router.get("/dictionary/lookup", response_model=DictionaryLookup)
async def dictionary_lookup(
    word: Annotated[str, Query(min_length=1, max_length=300)],
    request: Request,
) -> DictionaryLookup:
    service: DictionaryService = request.app.state.dictionary
    return await service.lookup(word)
