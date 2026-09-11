"""Tests for the Bíblia cockpit: registry, parser, provider, studies, routes."""

from __future__ import annotations

import os

import httpx
import pytest

from app.core.db import Database
from app.services.bible_books import BOOKS, all_profiles
from app.services.bible_parser import BibleReferenceError, parse_reference
from app.services.bible_provider import (
    BibleDbCache,
    BibleNotConfiguredError,
    BibleTextProvider,
    BibleTranslationUnavailableError,
    passage_id_for,
)
from app.services.bible_studies import BibleStudyService, LLMSchemaMismatchError
from app.services.llm import LLMBudgetExceeded, LLMJsonValidationError
from tests.backend.helpers import ClientFactory, FakeLLM, make_mock_http

SAMPLE_REPORT = {
    "text_literary": {
        "genre": "Epístola",
        "authorial_tone": "Solemne y pastoral",
        "unit_division": "Unidad de consuelo final del capítulo 8",
    },
    "historical_grammatical": {
        "author": "Pablo",
        "recipients": "Iglesia en Roma",
        "date": "≈ 57 d.C.",
        "geopolitical_context": "Roma, capital del imperio",
        "occasion": "Exposición del evangelio",
    },
    "lexical_exegesis": [
        {
            "term": "πάντα",
            "transliteration": "panta",
            "lemma": "πᾶς",
            "parsing": "acusativo plural neutro",
            "contextual_definition": "todas las cosas",
            "consensus_note": "Uso inclusivo en contexto",
        }
    ],
    "redemptive_theological": {
        "placement_redemptive_history": "Redención consumada en Cristo",
        "cross_references": ["Jn 10:28-29"],
        "christological_significance": "Seguridad en el amor de Cristo",
    },
    "core_principle": "Nada separa al creyente del amor de Dios en Cristo.",
    "practical_application": {
        "action_items": ["Memorizar Rm 8:38-39"],
        "reflection_prompts": ["¿Dónde temo ser separado de Cristo?"],
        "obedience_areas": ["Confiar en la perseverancia final"],
    },
    "guardrail_notes": "Lectura histórico-gramatical; sin alegorización.",
}


def make_bible_handler(passage_content: str = "texto del pasaje"):
    catalog = {
        "spa": [
            {"id": "bible-ntv", "abbreviation": "NTV", "name": "Nueva Traducción Viviente"},
            {"id": "bible-rvr09", "abbreviation": "RVR09", "name": "Reina Valera 1909"},
        ],
        "eng": [
            {"id": "bible-niv", "abbreviation": "NIV", "name": "New International Version"},
        ],
        "por": [
            {"id": "bible-nvt", "abbreviation": "NVT", "name": "Nova Versão Transformadora"},
        ],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/bibles"):
            language = (request.url.params.get("language") or "spa").lower()
            return httpx.Response(200, json={"data": catalog.get(language, [])})
        if "/passages/" in path:
            return httpx.Response(
                200,
                json={
                    "data": {
                        "content": passage_content,
                        "reference": "Romanos 8:31-39",
                        "verseCount": 9,
                        "copyright": "Mock © 2026 public domain",
                    }
                },
            )
        return httpx.Response(404, json={"message": "not found"})

    return handler


def test_books_registry_has_66_unique_books() -> None:
    codes = [book.code for book in BOOKS]
    assert len(codes) == 66
    assert len(set(codes)) == 66
    assert len(all_profiles()) == 66
    nt = [book for book in BOOKS if book.testament == "NT"]
    assert len(nt) == 27


def test_parser_resolves_names_across_languages() -> None:
    assert parse_reference("Romanos 8:31-39").book_code == "ROM"
    assert parse_reference("Rm 8:31-39").chapter == 8
    assert parse_reference("João 3:16").book_code == "JHN"
    assert parse_reference("Jo 3:16").book_code == "JHN"  # ambiguous 'Jo' prefers João
    assert parse_reference("Juan 3:16").book_code == "JHN"
    assert parse_reference("Gênesis 1").start_verse is None
    assert parse_reference("Genesis 1:1").start_verse == 1
    one_cor = parse_reference("1 Coríntios 13:4-7")
    assert one_cor.book_code == "1CO"
    assert one_cor.end_verse == 7


def test_parser_rejects_invalid_references() -> None:
    with pytest.raises(BibleReferenceError):
        parse_reference("Libro Inexistente 3:16")
    with pytest.raises(BibleReferenceError):
        parse_reference("Romanos 8:40-10")  # end before start
    with pytest.raises(BibleReferenceError):
        parse_reference("Romanos")


def test_passage_id_building() -> None:
    ref = parse_reference("Romanos 8:31-39")
    assert passage_id_for(ref) == "ROM.8.31-ROM.8.39"
    single = parse_reference("João 3:16")
    assert passage_id_for(single) == "JHN.3.16"
    chapter = parse_reference("Isaías 53")
    assert passage_id_for(chapter) == "ISA.53"


async def test_bible_db_cache_round_trip(database: Database) -> None:
    cache = BibleDbCache(database, ttl_seconds=7 * 86400)
    assert await cache.get("b1", "ROM.8") is None
    await cache.put("b1", "ROM.8", "texto", "Mock ©")
    assert await cache.get("b1", "ROM.8") == ("texto", "Mock ©")


async def test_provider_fetches_and_caches(database: Database) -> None:
    client = make_mock_http(make_bible_handler("texto del pasaje"))
    cache = BibleDbCache(database, ttl_seconds=7 * 86400)
    provider = BibleTextProvider(
        client,
        base_url="https://example.test/v1",
        api_key="test-key",
        default_translation="RVR09",
        cache=cache,
    )
    ref = parse_reference("Rm 8:31-39", translation="RVR09")
    first = await provider.fetch_text(ref, "RVR09")
    assert first == "texto del pasaje"
    # Copyright survives both the live fetch and the SQLite cache hit.
    content, copyright_first = await provider.fetch_text_with_copyright(ref, "RVR09")
    content, copyright_second = await provider.fetch_text_with_copyright(ref, "RVR09")
    assert content == "texto del pasaje"
    assert copyright_first == "Mock © 2026 public domain"
    assert copyright_second == "Mock © 2026 public domain"


async def test_provider_requires_key() -> None:
    provider = BibleTextProvider(
        make_mock_http(make_bible_handler()),
        base_url="https://example.test/v1",
        api_key="",
        default_translation="RVR09",
    )
    with pytest.raises(BibleNotConfiguredError):
        await provider.fetch_text(parse_reference("Rm 8:31-39"), "RVR09")


async def test_provider_rejects_unknown_translation() -> None:
    provider = BibleTextProvider(
        make_mock_http(make_bible_handler()),
        base_url="https://example.test/v1",
        api_key="k",
        default_translation="RVR09",
    )
    with pytest.raises(BibleTranslationUnavailableError):
        await provider.fetch_text(parse_reference("Rm 8:31-39"), "NTV99")


async def test_study_service_persists_and_reads_back(database: Database) -> None:
    client = make_mock_http(make_bible_handler("texto del pasaje"))
    provider = BibleTextProvider(
        client,
        base_url="https://example.test/v1",
        api_key="k",
        default_translation="RVR09",
    )
    llm = FakeLLM(SAMPLE_REPORT)
    service = BibleStudyService(database, llm, provider)

    record = await service.create_study("Rm 8:31-39", translation="RVR09")
    assert record.id > 0
    assert record.reference == "Romanos 8:31-39"
    assert record.translation == "RVR09"
    assert record.passage_text == "texto del pasaje"
    # Authoritative echo overrides whatever the model claimed.
    assert record.report.reference == "Romanos 8:31-39"
    assert record.report.core_principle == SAMPLE_REPORT["core_principle"]

    summaries = await service.list_studies()
    assert [item.id for item in summaries] == [record.id]

    loaded = await service.get_study(record.id)
    assert loaded is not None
    assert loaded.report.text_literary.genre == "Epístola"
    assert await service.delete_study(record.id) is True
    assert await service.get_study(record.id) is None


def test_books_endpoint(client_factory: ClientFactory) -> None:
    with client_factory() as client:
        response = client.get("/api/bible/books")
        assert response.status_code == 200
        assert len(response.json()) == 66


def test_passage_endpoint_requires_key(client_factory: ClientFactory) -> None:
    with client_factory() as client:
        response = client.get("/api/bible/passage", params={"reference": "Rm 8:31-39"})
        assert response.status_code == 503


def test_study_endpoint_flow_with_key(
    client_factory: ClientFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("BIBLE_API_KEY", "test-key")
    from app.core.config import get_settings

    get_settings.cache_clear()
    try:
        with client_factory(
            handler=make_bible_handler("texto do capítulo"), llm=FakeLLM(SAMPLE_REPORT)
        ) as client:
            books = client.get("/api/bible/books").json()
            assert len(books) == 66

            passage = client.get("/api/bible/passage", params={"reference": "Rm 8:31-39"})
            assert passage.status_code == 200
            body_passage = passage.json()
            assert body_passage["passage_text"] == "texto do capítulo"
            assert body_passage["copyright"] == "Mock © 2026 public domain"

            created = client.post("/api/bible/study", json={"reference": "Rm 8:31-39"})
            assert created.status_code == 201
            body = created.json()
            assert body["report"]["core_principle"] == SAMPLE_REPORT["core_principle"]
            assert body["report"]["reference"] == "Romanos 8:31-39"

            history = client.get("/api/bible/studies").json()
            assert [item["id"] for item in history] == [body["id"]]

            detail = client.get(f"/api/bible/studies/{body['id']}")
            assert detail.status_code == 200
            assert detail.json()["translation"] == "NTV"

            assert client.delete(f"/api/bible/studies/{body['id']}").status_code == 204
            assert client.get(f"/api/bible/studies/{body['id']}").status_code == 404
    finally:
        get_settings.cache_clear()
        os.environ.pop("BIBLE_API_KEY", None)


def test_study_endpoint_rejects_bad_reference(
    client_factory: ClientFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("BIBLE_API_KEY", "test-key")
    from app.core.config import get_settings

    get_settings.cache_clear()
    try:
        with client_factory(handler=make_bible_handler(), llm=FakeLLM(SAMPLE_REPORT)) as client:
            response = client.post("/api/bible/study", json={"reference": "zzz 9:9"})
            assert response.status_code == 422
    finally:
        get_settings.cache_clear()
        os.environ.pop("BIBLE_API_KEY", None)


async def test_provider_resolves_versions_across_languages() -> None:
    provider = BibleTextProvider(
        make_mock_http(make_bible_handler("texto")),
        base_url="https://example.test/v1",
        api_key="k",
        default_translation="NTV",
    )
    assert await provider.resolve_bible_id("NIV") == "bible-niv"
    assert await provider.resolve_bible_id("NVT") == "bible-nvt"
    assert await provider.resolve_bible_id("Nueva Traducción Viviente") == "bible-ntv"
    available = await provider.available_translations()
    abbreviations = {row["abbreviation"] for row in available}
    languages = {row["language"] for row in available}
    assert {"NTV", "NIV", "NVT"} <= abbreviations
    assert {"spa", "eng", "por"} <= languages


def test_translations_and_prefs_endpoints(
    client_factory: ClientFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("BIBLE_API_KEY", "test-key")
    from app.core.config import get_settings

    get_settings.cache_clear()
    try:
        with client_factory(handler=make_bible_handler("texto")) as client:
            prefs = client.get("/api/bible/prefs")
            assert prefs.status_code == 200
            assert prefs.json() == {"es": "NTV", "en": "NIV", "pt": "NVT"}

            rows = client.get("/api/bible/translations").json()
            abbreviations = {row["abbreviation"] for row in rows}
            assert {"NTV", "NIV", "NVT"} <= abbreviations
            languages = {row["language"] for row in rows}
            assert {"spa", "eng", "por"} <= languages
    finally:
        get_settings.cache_clear()
        os.environ.pop("BIBLE_API_KEY", None)


def test_passage_with_explicit_translation(
    client_factory: ClientFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("BIBLE_API_KEY", "test-key")
    from app.core.config import get_settings

    get_settings.cache_clear()
    try:
        with client_factory(handler=make_bible_handler("english text")) as client:
            response = client.get(
                "/api/bible/passage",
                params={"reference": "João 3:16", "translation": "NIV"},
            )
            assert response.status_code == 200
            body = response.json()
            assert body["ref"]["translation"] == "NIV"
            assert body["passage_text"] == "english text"
    finally:
        get_settings.cache_clear()
        os.environ.pop("BIBLE_API_KEY", None)


async def test_provider_prefix_fallback_resolves_niv11() -> None:
    """API.Bible catalogues the NIV as 'NIV11'; label 'NIV' must still resolve."""

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/bibles"):
            language = (request.url.params.get("language") or "spa").lower()
            data = (
                [
                    {
                        "id": "bible-niv11",
                        "abbreviation": "NIV11",
                        "name": "New International Version",
                    }
                ]
                if language == "eng"
                else []
            )
            return httpx.Response(200, json={"data": data})
        return httpx.Response(404, json={"message": "not found"})

    provider = BibleTextProvider(
        make_mock_http(handler),
        base_url="https://example.test/v1",
        api_key="k",
        default_translation="NTV",
    )
    assert await provider.resolve_bible_id("NIV") == "bible-niv11"


async def test_study_service_uses_selected_output_language(database: Database) -> None:
    client = make_mock_http(make_bible_handler("For God so loved the world"))
    provider = BibleTextProvider(
        client,
        base_url="https://example.test/v1",
        api_key="k",
        default_translation="NTV",
    )
    llm = FakeLLM(SAMPLE_REPORT)
    service = BibleStudyService(database, llm, provider)

    await service.create_study("João 3:16", translation="NIV", language="en")
    system = llm.calls[0]["system"]
    user = llm.calls[0]["user"]
    assert "MANDATORY GUARDRAILS" in system
    assert "Work in English" in system
    assert "Passage studied:" in user

    llm2 = FakeLLM(SAMPLE_REPORT)
    service2 = BibleStudyService(database, llm2, provider)
    await service2.create_study("Rm 8:31-39", translation="NTV", language="es")
    assert "GUARDARRAILS OBLIGATORIOS" in llm2.calls[0]["system"]


def test_study_route_accepts_language_param(
    client_factory: ClientFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("BIBLE_API_KEY", "test-key")
    from app.core.config import get_settings

    get_settings.cache_clear()
    try:
        with client_factory(
            handler=make_bible_handler("texto"), llm=FakeLLM(SAMPLE_REPORT)
        ) as client:
            created = client.post(
                "/api/bible/study",
                json={"reference": "João 3:16", "translation": "NIV", "language": "en"},
            )
            assert created.status_code == 201
            assert created.json()["report"]["core_principle"] == SAMPLE_REPORT["core_principle"]
    finally:
        get_settings.cache_clear()
        os.environ.pop("BIBLE_API_KEY", None)


async def test_study_retries_once_on_json_validation_failure(database: Database) -> None:
    calls: list[dict] = []

    class FlakyLLM:
        enabled = True

        async def complete_json(
            self, *, system: str, user: str, max_tokens: int, temperature: float
        ):
            calls.append({"system": system, "temperature": temperature})
            if len(calls) == 1:
                raise LLMJsonValidationError(
                    "LLM request failed (400): {\"error\": {\"code\": \"json_validate_failed\", "
                    "\"failed_generation\": \"{\\\"text_liter\\\"\"}}"
                )
            return SAMPLE_REPORT

    provider = BibleTextProvider(
        make_mock_http(make_bible_handler("english text")),
        base_url="https://example.test/v1",
        api_key="k",
        default_translation="NTV",
    )
    service = BibleStudyService(database, FlakyLLM(), provider)  # type: ignore[arg-type]
    record = await service.create_study("João 3:16", translation="NIV", language="en")
    assert record.report.reference == "João 3:16"
    assert len(calls) == 2
    assert "Return ONLY" in calls[1]["system"]
    assert calls[1]["temperature"] == 0.1


def _invalid_shape_report() -> dict:
    """A schema-valid JSON payload that fails BibleStudy validation."""
    bad = dict(SAMPLE_REPORT)
    bad["lexical_exegesis"] = SAMPLE_REPORT["lexical_exegesis"] * 4  # max_length=3
    return bad


async def test_study_retries_schema_mismatch_with_field_path_hint(
    database: Database,
) -> None:
    """A wrong-shape response retries once with a hint naming the failed field."""
    calls: list[dict] = []

    class ShapeFlakyLLM:
        enabled = True

        async def complete_json(
            self, *, system: str, user: str, max_tokens: int, temperature: float
        ):
            calls.append({"system": system, "temperature": temperature})
            if len(calls) == 1:
                return _invalid_shape_report()
            return SAMPLE_REPORT

    provider = BibleTextProvider(
        make_mock_http(make_bible_handler("english text")),
        base_url="https://example.test/v1",
        api_key="k",
        default_translation="NTV",
    )
    service = BibleStudyService(database, ShapeFlakyLLM(), provider)  # type: ignore[arg-type]
    record = await service.create_study("João 3:16", translation="NIV", language="en")

    assert record.report.reference == "João 3:16"
    assert len(calls) == 2
    # The hint must carry the *actual* failing field path, not just fire a retry.
    assert "lexical_exegesis" in calls[1]["system"]
    # ...and be the schema hint, not the JSON-syntax one.
    assert "MANDATORY CORRECTION" in calls[1]["system"]
    assert "Return ONLY" not in calls[1]["system"]
    # The first attempt still got the plain system prompt.
    assert "MANDATORY CORRECTION" not in calls[0]["system"]
    assert calls[1]["temperature"] == 0.1


async def test_study_exhausted_schema_mismatch_raises_typed_error(
    database: Database,
) -> None:
    """Both attempts wrong-shape -> LLMSchemaMismatchError naming the field."""
    calls: list[dict] = []

    class AlwaysWrongShapeLLM:
        enabled = True

        async def complete_json(
            self, *, system: str, user: str, max_tokens: int, temperature: float
        ):
            calls.append({"system": system})
            return _invalid_shape_report()

    provider = BibleTextProvider(
        make_mock_http(make_bible_handler("english text")),
        base_url="https://example.test/v1",
        api_key="k",
        default_translation="NTV",
    )
    service = BibleStudyService(
        database,
        AlwaysWrongShapeLLM(),  # type: ignore[arg-type]
        provider,
    )
    with pytest.raises(LLMSchemaMismatchError) as excinfo:
        await service.create_study("João 3:16", translation="NIV", language="en")

    assert len(calls) == 2
    message = str(excinfo.value)
    assert "lexical_exegesis" in message
    # The model's own field values must never be echoed into the error.
    assert "input_value" not in message
    assert "panta" not in message


def test_study_route_maps_schema_mismatch_to_friendly_detail(
    client_factory: ClientFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An exhausted schema mismatch surfaces a friendly detail, not a raw repr."""
    monkeypatch.setenv("BIBLE_API_KEY", "test-key")
    from app.core.config import get_settings

    class AlwaysWrongShapeLLM:
        enabled = True

        async def complete_json(
            self, *, system: str, user: str, max_tokens: int = 1024, temperature: float = 0.2
        ):
            return _invalid_shape_report()

    get_settings.cache_clear()
    try:
        with client_factory(
            handler=make_bible_handler("texto do capítulo"),
            llm=AlwaysWrongShapeLLM(),  # type: ignore[arg-type]
        ) as client:
            response = client.post("/api/bible/study", json={"reference": "Rm 8:31-39"})
            assert response.status_code == 502
            body = response.text
            assert "vuelve a intentarlo" in body
            assert "input_value" not in body
            assert "ValidationError" not in body
    finally:
        get_settings.cache_clear()
        os.environ.pop("BIBLE_API_KEY", None)


def test_study_route_maps_budget_exceeded_to_429(
    client_factory: ClientFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """LLMBudgetExceeded must reach the app's 429 handler, not become a 502."""
    monkeypatch.setenv("BIBLE_API_KEY", "test-key")
    from app.core.config import get_settings

    class BudgetLLM:
        enabled = True

        async def complete_json(
            self, *, system: str, user: str, max_tokens: int = 1024, temperature: float = 0.2
        ):
            raise LLMBudgetExceeded("LLM daily limit reached")

    get_settings.cache_clear()
    try:
        with client_factory(
            handler=make_bible_handler("texto do capítulo"),
            llm=BudgetLLM(),  # type: ignore[arg-type]
        ) as client:
            response = client.post("/api/bible/study", json={"reference": "Rm 8:31-39"})
            assert response.status_code == 429
            assert response.json()["detail"] == "LLM daily limit reached"
    finally:
        get_settings.cache_clear()
        os.environ.pop("BIBLE_API_KEY", None)
