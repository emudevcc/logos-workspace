"""Endpoint tests for the content routers."""

from __future__ import annotations

import httpx

from tests.backend.helpers import ClientFactory, FakeLLM, build_rss


def test_word_of_day_endpoint(client_factory: ClientFactory) -> None:
    with client_factory() as client:
        response = client.get("/api/word-of-day")
        assert response.status_code == 200
        data = response.json()
        assert data["expression"]
        assert len(data["examples"]) == 2


def test_word_of_day_random_endpoint_falls_back_to_curated(client_factory: ClientFactory) -> None:
    # LLM disabled → the endpoint degrades to the curated random pool.
    with client_factory(llm=FakeLLM(enabled=False)) as client:
        response = client.get("/api/word-of-day/random")
        assert response.status_code == 200
        data = response.json()
        assert data["expression"]
        assert len(data["examples"]) == 2


def test_word_of_day_random_endpoint_generates_with_llm(client_factory: ClientFactory) -> None:
    llm = FakeLLM(
        result={
            "expression": "to run the numbers",
            "kind": "collocation",
            "ipa": "/rʌn ðə ˈnʌmbəz/",
            "register_tag": "Professional",
            "definition": "To review the figures before deciding.",
            "examples": [
                "Let's run the numbers before committing.",
                "Run the numbers again for Q3.",
            ],
        }
    )
    with client_factory(llm=llm) as client:
        response = client.get("/api/word-of-day/random")
        assert response.status_code == 200
        data = response.json()
        assert data["expression"] == "to run the numbers"
        assert len(data["examples"]) == 2


def test_news_endpoint_returns_headlines_and_vocab(client_factory: ClientFactory) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, text=build_rss([{"title": "Headline", "link": "https://e.com/1"}])
        )

    llm = FakeLLM(result={"terms": [{"term": "term", "definition": "definition"}]})
    with client_factory(handler=handler, llm=llm) as client:
        response = client.get("/api/news")
        assert response.status_code == 200
        data = response.json()
        assert data["headlines"][0]["title"] == "Headline"
        assert data["headlines"][0]["vocab"][0]["term"] == "term"


def test_podcast_endpoint_returns_digest(client_factory: ClientFactory) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text=build_rss(
                [
                    {
                        "title": "Episode",
                        "link": "https://e.com/1",
                        "summary": "Summary text",
                        "audio_url": "https://e.com/a.mp3",
                    }
                ]
            ),
        )

    with client_factory(handler=handler, llm=FakeLLM(enabled=False)) as client:
        response = client.get("/api/podcast-digest")
        assert response.status_code == 200
        data = response.json()
        assert data["episodes"][0]["title"] == "Episode"
        assert data["episodes"][0]["audio_url"] == "https://e.com/a.mp3"
