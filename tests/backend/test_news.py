"""Unit tests for the News Pulse service."""

from __future__ import annotations

import httpx

from app.services.news import NEWS_FEEDS, NewsService
from tests.backend.helpers import FakeLLM, build_rss, make_mock_http


def test_news_feeds_are_configured() -> None:
    assert len(NEWS_FEEDS) >= 6


async def test_pulse_returns_headline_with_vocab() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text=build_rss(
                [
                    {
                        "title": "Chipmakers rally on AI demand",
                        "link": "https://e.com/1",
                        "published": "Mon, 01 Jan 2024 09:00:00 GMT",
                        "summary": "summary",
                    }
                ]
            ),
        )

    http = make_mock_http(handler)
    llm = FakeLLM(result={"terms": [{"term": "rally", "definition": "a sustained rise"}]})
    service = NewsService(http, llm, feeds=(("Test", "https://feed.example.com"),))

    pulse = await service.pulse()

    assert len(pulse.headlines) == 1
    headline = pulse.headlines[0]
    assert headline.source == "Test"
    assert headline.title == "Chipmakers rally on AI demand"
    assert headline.vocab[0].term == "rally"


async def test_pulse_skips_failed_feed() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(500)
        return httpx.Response(
            200, text=build_rss([{"title": "OK headline", "link": "https://e.com/1"}])
        )

    http = make_mock_http(handler)
    llm = FakeLLM(enabled=False)
    service = NewsService(
        http,
        llm,
        feeds=(
            ("Bad", "https://bad.example.com"),
            ("Good", "https://good.example.com"),
        ),
    )

    pulse = await service.pulse()

    assert len(pulse.headlines) == 1
    assert pulse.headlines[0].title == "OK headline"


async def test_no_llm_key_means_empty_vocab() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, text=build_rss([{"title": "A headline", "link": "https://e.com/1"}])
        )

    http = make_mock_http(handler)
    llm = FakeLLM(enabled=False)
    service = NewsService(http, llm, feeds=(("Test", "https://feed.example.com"),))

    pulse = await service.pulse()

    assert pulse.headlines[0].vocab == []


async def test_invalid_llm_vocab_degrades_to_empty() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, text=build_rss([{"title": "A headline", "link": "https://e.com/1"}])
        )

    http = make_mock_http(handler)
    llm = FakeLLM(result={"terms": "not-a-list"})  # malformed LLM output
    service = NewsService(http, llm, feeds=(("Test", "https://feed.example.com"),))

    pulse = await service.pulse()

    assert len(pulse.headlines) == 1
    assert pulse.headlines[0].vocab == []


async def test_pulse_is_cached() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200, text=build_rss([{"title": "Headline", "link": "https://e.com/1"}])
        )

    http = make_mock_http(handler)
    llm = FakeLLM(enabled=False)
    service = NewsService(http, llm, feeds=(("Test", "https://feed.example.com"),))

    await service.pulse()
    await service.pulse()

    assert calls == 1


async def test_pulse_refresh_bypasses_cache() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200, text=build_rss([{"title": "Headline", "link": "https://e.com/1"}])
        )

    http = make_mock_http(handler)
    llm = FakeLLM(enabled=False)
    service = NewsService(http, llm, feeds=(("Test", "https://feed.example.com"),))

    await service.pulse()
    await service.pulse(refresh=True)

    assert calls == 2
