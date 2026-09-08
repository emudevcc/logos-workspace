"""Brazilian Portuguese news pulse: headlines from PT-BR feeds.

Feeds are fetched concurrently and cached (TTL); a single failing feed is
skipped rather than failing the whole pulse. No LLM is used, so the card works
with zero budget and degrades gracefully offline.
"""

from __future__ import annotations

import asyncio
import logging
import random

import httpx

from app.core.cache import TTLCache
from app.schemas.pt import PtHeadline, PtNewsPulse
from app.services.rss import fetch_feed

logger = logging.getLogger(__name__)

PT_NEWS_FEEDS: tuple[tuple[str, str], ...] = (
    ("G1", "https://g1.globo.com/rss/g1/"),
    ("Exame", "https://exame.com/feed/"),
    ("Tecnoblog", "https://tecnoblog.net/feed/"),
)

MAX_HEADLINES = 5


class PtNewsService:
    def __init__(
        self,
        client: httpx.AsyncClient,
        ttl_seconds: float = 600.0,
        feeds: tuple[tuple[str, str], ...] = PT_NEWS_FEEDS,
    ) -> None:
        self._client = client
        self._feeds = feeds
        self._cache = TTLCache[PtNewsPulse](ttl_seconds)

    async def pulse(self, *, refresh: bool = False) -> PtNewsPulse:
        if not refresh:
            return await self._cache.get("pt-news", self._fetch_pulse)
        pulse = await self._fetch_pulse()
        self._cache.put("pt-news", pulse)
        return pulse

    async def _fetch_pulse(self) -> PtNewsPulse:
        results = await asyncio.gather(
            *(fetch_feed(self._client, url, limit=3) for _, url in self._feeds),
            return_exceptions=True,
        )
        items: list[PtHeadline] = []
        for (name, _), result in zip(self._feeds, results, strict=True):
            if isinstance(result, list):
                for item in result:
                    if item.title and item.link:
                        items.append(PtHeadline(title=item.title, source=name, url=item.link))
        random.shuffle(items)
        return PtNewsPulse(headlines=items[:MAX_HEADLINES])
