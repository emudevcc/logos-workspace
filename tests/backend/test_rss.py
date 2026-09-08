"""Unit tests for RSS fetching and normalization."""

from __future__ import annotations

import httpx
import pytest

from app.services.rss import FeedError, fetch_feed
from tests.backend.helpers import build_rss


def _client(body: str, status: int = 200) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, text=body)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_fetch_feed_parses_items_and_cleans_html() -> None:
    xml = build_rss(
        [
            {
                "title": "First",
                "link": "https://e.com/1",
                "published": "Mon, 01 Jan 2024 09:00:00 GMT",
                "summary": "<p>Hello <b>world</b></p>",
                "audio_url": "https://e.com/a.mp3",
            }
        ]
    )
    async with _client(xml) as http:
        items = await fetch_feed(http, "https://feed.example.com/rss")
    assert len(items) == 1
    item = items[0]
    assert item.title == "First"
    assert item.link == "https://e.com/1"
    assert item.published == "Mon, 01 Jan 2024 09:00:00 GMT"
    assert item.summary == "Hello world"
    assert item.audio_url == "https://e.com/a.mp3"


async def test_fetch_feed_respects_limit() -> None:
    xml = build_rss([{"title": f"T{i}", "link": f"https://e.com/{i}"} for i in range(5)])
    async with _client(xml) as http:
        items = await fetch_feed(http, "https://feed.example.com/rss", limit=2)
    assert len(items) == 2


async def test_fetch_feed_raises_on_http_error() -> None:
    async with _client("", status=500) as http:
        with pytest.raises(FeedError):
            await fetch_feed(http, "https://feed.example.com/rss")


async def test_fetch_feed_raises_on_invalid_xml() -> None:
    async with _client("this is not xml at all") as http:
        with pytest.raises(FeedError):
            await fetch_feed(http, "https://feed.example.com/rss")
