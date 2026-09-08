"""Unit tests for the Podcast Digest service."""

from __future__ import annotations

import httpx

from app.services.podcast import PODCAST_FEEDS, PodcastService
from tests.backend.helpers import FakeLLM, build_rss, make_mock_http

_FEEDS = (("Test", "https://feed.example.com"),)


def test_podcast_feeds_are_configured() -> None:
    assert len(PODCAST_FEEDS) >= 5


def _handler() -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text=build_rss(
                [
                    {
                        "title": "Episode One",
                        "link": "https://e.com/1",
                        "published": "Mon, 01 Jan 2024 09:00:00 GMT",
                        "summary": "First summary text",
                        "audio_url": "https://e.com/1.mp3",
                    },
                    {
                        "title": "Episode Two",
                        "link": "https://e.com/2",
                        "summary": "Second summary text",
                        "audio_url": "https://e.com/2.mp3",
                    },
                ]
            ),
        )

    return make_mock_http(handler)


async def test_digest_uses_llm_brief_when_enabled() -> None:
    llm = FakeLLM(
        result={
            "title": "Morning Brief",
            "brief": ["p1", "p2", "p3"],
            "key_terms": [{"term": "term", "definition": "definition"}],
        }
    )
    service = PodcastService(_handler(), llm, feeds=_FEEDS)

    digest = await service.digest()

    assert digest.title == "Morning Brief"
    assert digest.brief == ["p1", "p2", "p3"]
    assert digest.key_terms[0].term == "term"
    assert len(digest.episodes) == 1
    assert digest.episodes[0].audio_url == "https://e.com/1.mp3"


async def test_digest_falls_back_to_summaries_without_llm() -> None:
    llm = FakeLLM(enabled=False)
    service = PodcastService(_handler(), llm, feeds=_FEEDS)

    digest = await service.digest()

    assert digest.title == "Morning Brief"
    assert digest.brief == ["First summary text"]
    assert digest.key_terms == []


async def test_digest_falls_back_on_invalid_llm_output() -> None:
    llm = FakeLLM(result={"brief": "not-a-list"})  # malformed LLM output
    service = PodcastService(_handler(), llm, feeds=_FEEDS)

    digest = await service.digest()

    assert digest.title == "Morning Brief"
    assert digest.brief == ["First summary text"]


async def test_digest_is_cached() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200, text=build_rss([{"title": "Ep", "link": "https://e.com/1", "summary": "s"}])
        )

    http = make_mock_http(handler)
    llm = FakeLLM(enabled=False)
    service = PodcastService(http, llm, feeds=_FEEDS)

    await service.digest()
    await service.digest()

    assert calls == 1


async def test_digest_refresh_bypasses_cache() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200, text=build_rss([{"title": "Ep", "link": "https://e.com/1", "summary": "s"}])
        )

    http = make_mock_http(handler)
    llm = FakeLLM(enabled=False)
    service = PodcastService(http, llm, feeds=_FEEDS)

    await service.digest()
    await service.digest(refresh=True)

    assert calls == 2
