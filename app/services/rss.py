"""RSS/Atom fetching and normalization.

Feeds are the free, keyless backbone for news and podcast content. Parsing
normalizes each entry into a small ``FeedItem`` and strips HTML from text
fields so the frontend renders clean strings.
"""

from __future__ import annotations

import asyncio
import html
import re
from dataclasses import dataclass
from typing import Any

import feedparser  # type: ignore[import-untyped]
import httpx

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


class FeedError(RuntimeError):
    """Raised when a feed cannot be fetched or parsed."""


@dataclass(frozen=True, slots=True)
class FeedItem:
    title: str
    link: str
    published: str | None
    summary: str | None
    audio_url: str | None


async def fetch_feed(client: httpx.AsyncClient, url: str, *, limit: int = 10) -> list[FeedItem]:
    """Fetch and parse a feed, returning up to ``limit`` newest entries."""
    try:
        response = await client.get(url)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise FeedError(f"Failed to fetch {url}: {exc}") from exc

    parsed = await asyncio.to_thread(feedparser.parse, response.content)
    if parsed.bozo and not parsed.entries:
        raise FeedError(f"Invalid feed {url}: {parsed.bozo_exception}")

    items: list[FeedItem] = []
    for entry in parsed.entries[:limit]:
        items.append(
            FeedItem(
                title=_clean(entry.get("title", "")) or "",
                link=str(entry.get("link", "")),
                published=_clean(entry.get("published")),
                summary=_clean(entry.get("summary")),
                audio_url=_extract_audio(entry),
            )
        )
    return items


def _extract_audio(entry: Any) -> str | None:
    for enclosure in entry.get("enclosures", []) or []:
        if isinstance(enclosure, dict) and str(enclosure.get("type", "")).startswith("audio/"):
            href = enclosure.get("href")
            if href:
                return str(href)
    return None


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    text = _HTML_TAG_RE.sub(" ", value)
    text = html.unescape(text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text or None
