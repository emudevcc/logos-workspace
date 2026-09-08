"""Tech & Business News Pulse: three curated headlines with key vocabulary.

Each source is fetched concurrently; a single failing feed is skipped rather
than failing the whole pulse. Vocabulary is extracted via the LLM when a key is
configured, otherwise the headline is returned without annotations.
"""

from __future__ import annotations

import asyncio
import logging
import random

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

from app.core.cache import TTLCache
from app.schemas.content import Headline, NewsPulse, VocabTerm
from app.services.llm import LLMError, LLMProvider
from app.services.rss import FeedItem, fetch_feed

logger = logging.getLogger(__name__)

NEWS_FEEDS: tuple[tuple[str, str], ...] = (
    ("BBC Technology", "http://feeds.bbci.co.uk/news/technology/rss.xml"),
    ("The Verge", "https://www.theverge.com/rss/index.xml"),
    ("The Guardian Technology", "https://www.theguardian.com/uk/technology/rss"),
    ("BBC Business", "http://feeds.bbci.co.uk/news/business/rss.xml"),
    ("NPR News", "https://feeds.npr.org/1001/rss.xml"),
    ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
)

_VOCAB_SYSTEM = (
    "You are an English vocabulary assistant for an advanced (C1/C2) learner. "
    "Given a news headline, extract up to 3 key words or collocations and write a "
    "brief learner-friendly definition for each. Respond ONLY with JSON shaped "
    'exactly like: {"terms": [{"term": "string", "definition": "string"}]}.'
)


class _LLMTerm(BaseModel):
    term: str
    definition: str


class _NewsVocab(BaseModel):
    model_config = ConfigDict(extra="ignore")

    terms: list[_LLMTerm]


class NewsService:
    def __init__(
        self,
        client: httpx.AsyncClient,
        llm: LLMProvider,
        feeds: tuple[tuple[str, str], ...] = NEWS_FEEDS,
        ttl_seconds: float = 600.0,
    ) -> None:
        self._client = client
        self._llm = llm
        self._feeds = feeds
        self._cache = TTLCache[NewsPulse](ttl_seconds)

    async def pulse(self, *, refresh: bool = False) -> NewsPulse:
        if not refresh:
            return await self._cache.get("news", self._fetch_pulse)
        pulse = await self._fetch_pulse()
        self._cache.put("news", pulse)
        return pulse

    async def _fetch_pulse(self) -> NewsPulse:
        results = await asyncio.gather(
            *(fetch_feed(self._client, url, limit=3) for _, url in self._feeds),
            return_exceptions=True,
        )
        items: list[tuple[str, FeedItem]] = []
        for (name, _), result in zip(self._feeds, results, strict=True):
            if isinstance(result, list):
                for item in result:
                    if item.title and item.link:
                        items.append((name, item))
        random.shuffle(items)
        headlines = await asyncio.gather(
            *(self._make_headline(name, item) for name, item in items[:5]),
            return_exceptions=True,
        )
        return NewsPulse(headlines=[h for h in headlines if isinstance(h, Headline)])

    async def _make_headline(self, name: str, item: FeedItem) -> Headline:
        vocab = await self._extract_vocab(item.title)
        return Headline(
            source=name,
            title=item.title,
            link=item.link,
            published=item.published,
            vocab=vocab,
        )

    async def _extract_vocab(self, title: str) -> list[VocabTerm]:
        if not self._llm.enabled:
            return []
        try:
            raw = await self._llm.complete_json(system=_VOCAB_SYSTEM, user=title, max_tokens=300)
            parsed = _NewsVocab.model_validate(raw)
        except (LLMError, ValidationError) as exc:
            logger.warning("Vocabulary extraction failed for %r: %s", title, exc)
            return []
        return [VocabTerm(term=t.term, definition=t.definition) for t in parsed.terms][:3]
