"""Daily Audio & Podcast Digest (Morning Brief).

Latest episodes are pulled from podcast RSS feeds. When an LLM key is
configured, a three-paragraph executive brief plus key terms are generated;
otherwise the digest falls back to the episodes' own summaries.
"""

from __future__ import annotations

import asyncio
import logging
import random

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.cache import TTLCache
from app.schemas.content import PodcastDigest, PodcastEpisode, VocabTerm
from app.services.llm import LLMError, LLMProvider
from app.services.rss import fetch_feed

logger = logging.getLogger(__name__)

PODCAST_FEEDS: tuple[tuple[str, str], ...] = (
    ("NPR Up First", "https://feeds.npr.org/510318/podcast.xml"),
    ("BBC Global News", "https://podcasts.files.bbci.co.uk/p02nq0gn.rss"),
    ("BBC 6 Minute English", "https://podcasts.files.bbci.co.uk/p02pc9tn.rss"),
    ("Learning English Conversations", "https://podcasts.files.bbci.co.uk/p02pc9zn.rss"),
    ("BBC Business Daily", "https://podcasts.files.bbci.co.uk/p002vsxs.rss"),
    ("NPR Planet Money", "https://feeds.npr.org/510289/podcast.xml"),
)

_BRIEF_SYSTEM = (
    "You are an executive briefing assistant. Given podcast episode titles and "
    "descriptions, write a concise 3-paragraph executive brief and list up to 5 "
    "key terms with definitions. Respond ONLY with JSON shaped exactly like: "
    '{"title": "string", "brief": ["paragraph1", "paragraph2", "paragraph3"], '
    '"key_terms": [{"term": "string", "definition": "string"}]}.'
)

_MAX_EPISODES = 6
_SUMMARY_LENGTH = 500


class PodcastError(RuntimeError):
    """Raised when the digest cannot be produced."""


class _LLMTerm(BaseModel):
    term: str
    definition: str


class _LLMBrief(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str
    brief: list[str]
    key_terms: list[_LLMTerm] = Field(default_factory=list)


class PodcastService:
    def __init__(
        self,
        client: httpx.AsyncClient,
        llm: LLMProvider,
        feeds: tuple[tuple[str, str], ...] = PODCAST_FEEDS,
        ttl_seconds: float = 600.0,
    ) -> None:
        self._client = client
        self._llm = llm
        self._feeds = feeds
        self._cache = TTLCache[PodcastDigest](ttl_seconds)

    async def digest(self, *, refresh: bool = False) -> PodcastDigest:
        if not refresh:
            return await self._cache.get("podcast", self._fetch_digest)
        digest = await self._fetch_digest()
        self._cache.put("podcast", digest)
        return digest

    async def _fetch_digest(self) -> PodcastDigest:
        episodes = await self._fetch_episodes()
        if not episodes:
            return PodcastDigest(title="Morning Brief", brief=[], episodes=[])

        title = "Morning Brief"
        brief = _fallback_brief(episodes)
        key_terms: list[VocabTerm] = []

        if self._llm.enabled:
            try:
                title, brief, key_terms = await self._llm_brief(episodes)
            except (LLMError, PodcastError) as exc:
                logger.warning("LLM brief failed, falling back to summaries: %s", exc)

        return PodcastDigest(
            title=title,
            brief=brief[:3],
            key_terms=key_terms,
            episodes=episodes,
        )

    async def _fetch_episodes(self) -> list[PodcastEpisode]:
        results = await asyncio.gather(
            *(fetch_feed(self._client, url, limit=1) for _, url in self._feeds),
            return_exceptions=True,
        )
        episodes: list[PodcastEpisode] = []
        for result in results:
            if isinstance(result, list):
                for item in result:
                    episodes.append(
                        PodcastEpisode(
                            title=item.title,
                            link=item.link,
                            published=item.published,
                            summary=item.summary,
                            audio_url=item.audio_url,
                        )
                    )
        # Randomize presentation so a refresh never shows the same feed order.
        random.shuffle(episodes)
        return episodes[:_MAX_EPISODES]

    async def _llm_brief(
        self, episodes: list[PodcastEpisode]
    ) -> tuple[str, list[str], list[VocabTerm]]:
        user = "\n\n".join(
            f"TITLE: {episode.title}\nDESCRIPTION: {episode.summary or ''}" for episode in episodes
        )
        raw = await self._llm.complete_json(system=_BRIEF_SYSTEM, user=user, max_tokens=700)
        try:
            parsed = _LLMBrief.model_validate(raw)
        except ValidationError as exc:
            raise PodcastError(f"LLM brief validation failed: {exc}") from exc
        key_terms = [VocabTerm(term=t.term, definition=t.definition) for t in parsed.key_terms][:5]
        return parsed.title, parsed.brief[:3], key_terms


def _fallback_brief(episodes: list[PodcastEpisode]) -> list[str]:
    brief: list[str] = []
    for episode in episodes:
        summary = episode.summary or episode.title
        brief.append(summary[:_SUMMARY_LENGTH])
    return brief
