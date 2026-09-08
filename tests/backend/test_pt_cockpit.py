"""Tests for the Português cockpit: content, seeding, and endpoints."""

from __future__ import annotations

from datetime import date

import httpx

from app.core.db import Database
from app.schemas.srs import CardCreateRequest
from app.services.pt_content import (
    FALLBACK_SENTENCES,
    MINIMAL_PAIRS_PT,
    PITFALLS_PT,
    RULE_COUNT,
    random_rule,
    random_word,
    rule_for_date,
    word_for_date,
)
from app.services.pt_seed import (
    PT_COGNATES_DECK_SLUG,
    PT_VOCAB_DECK_SLUG,
    seed_pt_decks,
)
from app.services.srs import SrsService
from app.services.srs_seed import seed_default_deck
from tests.backend.helpers import ClientFactory, FakeLLM, build_rss


def test_curated_content_pools_are_populated() -> None:
    assert len(MINIMAL_PAIRS_PT) > 8
    assert len(PITFALLS_PT) > 5
    assert len(FALLBACK_SENTENCES) > 8
    assert RULE_COUNT > 5


def test_word_of_day_is_stable_per_date() -> None:
    day = date(2026, 9, 8)
    first = word_for_date(day)
    second = word_for_date(day)
    assert first.expression == second.expression
    assert first.category in {"palavra", "expressao", "colocacao"}
    assert first.definition_pt and first.nota_es


def test_rule_rotation_is_stable_and_distinct_across_days() -> None:
    day = date(2026, 9, 8)
    assert rule_for_date(day) == rule_for_date(day)
    assert rule_for_date(day) != rule_for_date(date(2026, 9, 9))


def test_random_rule_excludes_current_title() -> None:
    current = rule_for_date(date.today())
    other = random_rule(exclude_title=current.title)
    assert other.title != current.title


def test_random_word_is_from_pool() -> None:
    word = random_word()
    assert word.expression
    assert word.nota_es


async def test_pt_seed_creates_pt_decks(database: Database) -> None:
    await seed_default_deck(database)
    await seed_pt_decks(database)
    service = SrsService(database)

    decks = await service.list_decks("pt")
    assert [d.slug for d in decks] == [PT_VOCAB_DECK_SLUG, PT_COGNATES_DECK_SLUG]
    assert (await service.stats("pt")).cards_total == 36
    assert (await service.stats("en")).cards_total == 12

    # Seeding is idempotent and no English deck is touched.
    await seed_pt_decks(database)
    assert len(await service.list_decks("pt")) == 2
    assert len(await service.list_decks("en")) == 1

    # Spanish scaffolding hints are persisted on the cards.
    cursor = await database.connection.execute(
        "SELECT l1_hint FROM cards WHERE deck_id = "
        "(SELECT id FROM decks WHERE slug = ?) LIMIT 1",
        (PT_COGNATES_DECK_SLUG,),
    )
    row = await cursor.fetchone()
    assert row is not None
    assert row["l1_hint"] != ""


async def test_add_card_persists_l1_hint(database: Database) -> None:
    await seed_pt_decks(database)
    service = SrsService(database)
    created = await service.add_card(
        CardCreateRequest(front="dar certo", back="funcionar", l1_hint="¡Ojo!"),
        cockpit="pt",
    )
    assert created.l1_hint == "¡Ojo!"
    fetched = await service.get_card(created.id)
    assert fetched is not None
    assert fetched.l1_hint == "¡Ojo!"


def test_word_of_day_endpoint(client_factory: ClientFactory) -> None:
    with client_factory() as client:
        response = client.get("/api/pt/word-of-day?date=2026-09-08")
        assert response.status_code == 200
        body = response.json()
        assert body["expression"] and body["definition_pt"] and body["nota_es"]

        random_body = client.get("/api/pt/word-of-day/random").json()
        assert random_body["expression"]


def test_grammar_endpoints(client_factory: ClientFactory) -> None:
    with client_factory() as client:
        rules = client.get("/api/pt/grammar/rules").json()
        assert len(rules) == RULE_COUNT

        rule_of_day = client.get("/api/pt/grammar/rule-of-day?date=2026-09-08")
        assert rule_of_day.status_code == 200
        assert rule_of_day.json()["title"]

        rule_title = rule_of_day.json()["title"]
        other = client.get(
            "/api/pt/grammar/rule-random",
            params={"exclude": rule_title},
        )
        assert other.status_code == 200
        assert other.json()["title"] != rule_title


def test_pronunciation_endpoints(client_factory: ClientFactory) -> None:
    with client_factory() as client:
        pairs = client.get("/api/pt/pronunciation/minimal-pairs").json()
        pitfalls = client.get("/api/pt/pronunciation/pitfalls").json()
        assert pairs and all("a" in pair and "b" in pair for pair in pairs)
        assert pitfalls and all(pitfall["tip_pt"] for pitfall in pitfalls)


def test_pt_news_returns_headlines(client_factory: ClientFactory) -> None:
    feed = build_rss(
        [
            {
                "title": "Notícia um",
                "link": "https://example.com/1",
                "summary": "Resumo.",
                "published": "Tue, 08 Sep 2026 10:00:00 GMT",
            },
            {
                "title": "Notícia dois",
                "link": "https://example.com/2",
                "summary": "Resumo 2.",
                "published": "Tue, 08 Sep 2026 11:00:00 GMT",
            },
        ]
    )

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=feed, headers={"Content-Type": "text/xml"})

    with client_factory(handler=handler) as client:
        response = client.get("/api/pt/news")
        assert response.status_code == 200
        body = response.json()
        assert body["headlines"]
        assert all(item["title"] for item in body["headlines"])


def test_grammar_coach_endpoint(client_factory: ClientFactory) -> None:
    result = {
        "resposta_pt": "Use o subjuntivo após 'espero que'.",
        "nota_es": "Igual que en español.",
        "exemplos": ["Espero que você venha."],
    }
    with client_factory(llm=FakeLLM(result)) as client:
        response = client.post("/api/pt/grammar/coach", json={"pergunta": "espero que + ?"})
        assert response.status_code == 200
        assert response.json()["resposta_pt"] == result["resposta_pt"]


def test_grammar_coach_requires_llm(client_factory: ClientFactory) -> None:
    with client_factory(llm=FakeLLM(enabled=False)) as client:
        response = client.post("/api/pt/grammar/coach", json={"pergunta": "teste"})
        assert response.status_code == 503


def test_practice_sentence_uses_llm_when_configured(client_factory: ClientFactory) -> None:
    result = {"frase": "A gente se vê amanhã.", "nota_es": "a gente = nosotros", "dica": "nasal"}
    with client_factory(llm=FakeLLM(result)) as client:
        response = client.get("/api/pt/practice/sentence")
        assert response.status_code == 200
        assert response.json()["frase"] == result["frase"]


def test_practice_sentence_falls_back_without_llm(client_factory: ClientFactory) -> None:
    with client_factory() as client:
        response = client.get("/api/pt/practice/sentence")
        assert response.status_code == 200
        assert response.json()["frase"]


def test_srs_pt_scoping_through_api(client_factory: ClientFactory) -> None:
    with client_factory() as client:
        pt_decks = client.get("/api/srs/decks?cockpit=pt").json()
        assert [deck["slug"] for deck in pt_decks] == [PT_VOCAB_DECK_SLUG, PT_COGNATES_DECK_SLUG]

        created = client.post(
            "/api/srs/cards?cockpit=pt",
            json={
                "front": "esquisito",
                "back": "estranho",
                "l1_hint": "No es 'exquisito'.",
                "register_tag": "Falso cognato",
            },
        )
        assert created.status_code == 201
        assert created.json()["l1_hint"] == "No es 'exquisito'."
        assert created.json()["deck_id"] == pt_decks[0]["id"]


def test_sentence_and_word_mock_llm_calls_are_json(client_factory: ClientFactory) -> None:
    sentence_llm = FakeLLM({"frase": "x", "nota_es": "", "dica": ""})
    with client_factory(llm=sentence_llm) as client:
        assert client.get("/api/pt/practice/sentence").status_code == 200

    coach_llm = FakeLLM({"resposta_pt": "ok", "nota_es": "", "exemplos": []})
    with client_factory(llm=coach_llm) as client:
        response = client.post("/api/pt/grammar/coach", json={"pergunta": "por que?"})
        assert response.status_code == 200
