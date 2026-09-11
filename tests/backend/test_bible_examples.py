"""Tests for the LLM-backed example-passage suggester and its endpoint."""

from __future__ import annotations

import pytest

from app.api.routes_bible import example_passages
from app.services.bible_examples import BiblePassageSuggester
from app.services.bible_parser import BibleReferenceError, parse_reference
from app.services.llm import LLMBudgetExceeded, LLMError, LLMNotConfiguredError
from tests.backend.helpers import ClientFactory, FakeLLM


class _MiniRequest:
    """Just enough of ``Request`` for a direct route call."""

    def __init__(self, suggester: object) -> None:
        self.app = type("App", (), {"state": type("State", (), {"bible_examples": suggester})})()


async def test_suggest_returns_only_parseable_references() -> None:
    llm = FakeLLM(
        result={
            "passages": [
                "Romanos 8:31-39",
                "NoExisteLibro 3:1",  # unparseable book
                "Salmos 23",
                "  ",  # blank
                "Juan",  # book with no chapter -> unparseable
                "Génesis 1:1-5",
            ]
        }
    )
    result = await BiblePassageSuggester(llm).suggest("es")

    assert result == ["Romanos 8:31-39", "Salmos 23", "Génesis 1:1-5"]
    # The contract: nothing returned could be rejected by the parser.
    for reference in result:
        parse_reference(reference)


async def test_suggest_drops_everything_when_nothing_is_valid() -> None:
    llm = FakeLLM(result={"passages": ["Nope 1:1", "TambiénNo 2:2"]})
    # All-invalid is an empty list, not an error.
    assert await BiblePassageSuggester(llm).suggest("es") == []


async def test_suggest_handles_non_string_entries() -> None:
    llm = FakeLLM(result={"passages": [1, None, "Salmos 23", {"x": 1}]})
    assert await BiblePassageSuggester(llm).suggest("es") == ["Salmos 23"]


async def test_suggest_ignores_missing_passages_field() -> None:
    llm = FakeLLM(result={"something_else": []})
    assert await BiblePassageSuggester(llm).suggest("es") == []


async def test_second_call_avoids_the_first_in_prompt() -> None:
    """The anti-repeat hint must actually be sent, not merely remembered."""
    llm = FakeLLM(result={"passages": ["Romanos 8:31-39", "Salmos 23"]})
    suggester = BiblePassageSuggester(llm)

    first = await suggester.suggest("es")
    assert first == ["Romanos 8:31-39", "Salmos 23"]
    # The first call had nothing to avoid yet.
    assert llm.calls[0]["user"] == ""

    await suggester.suggest("es")
    second_user = llm.calls[1]["user"]
    assert second_user != llm.calls[0]["user"]
    assert "Romanos 8:31-39" in second_user
    assert "Salmos 23" in second_user


async def test_recent_windows_are_independent_per_language() -> None:
    llm = FakeLLM(result={"passages": ["Romanos 8:31-39"]})
    suggester = BiblePassageSuggester(llm)

    await suggester.suggest("es")
    await suggester.suggest("en")

    # Switching language must not suppress the other language's chips.
    assert llm.calls[1]["user"] == ""


async def test_prompt_is_localized_per_language() -> None:
    llm = FakeLLM(result={"passages": ["Salmos 23"]})
    suggester = BiblePassageSuggester(llm)

    await suggester.suggest("es")
    await suggester.suggest("en")
    await suggester.suggest("pt")

    assert "Study" in llm.calls[1]["system"] or "study" in llm.calls[1]["system"]
    systems = [call["system"] for call in llm.calls]
    assert len(set(systems)) == 3


async def test_prompt_states_the_verse_range_guidance() -> None:
    llm = FakeLLM(result={"passages": ["Salmos 23"]})
    await BiblePassageSuggester(llm).suggest("en")
    # The parser cannot enforce a verse-count bound, so the prompt must ask.
    assert "5-15 verse" in llm.calls[0]["system"]


@pytest.mark.parametrize(
    "error",
    [LLMNotConfiguredError("no key"), LLMBudgetExceeded("limit"), LLMError("boom")],
)
async def test_suggest_propagates_llm_errors(error: LLMError) -> None:
    """The service does not swallow failures — that is the route's call."""

    class RaisingLLM:
        enabled = True

        async def complete_json(self, **kwargs: object) -> dict[str, object]:
            raise error

    with pytest.raises(type(error)):
        await BiblePassageSuggester(RaisingLLM()).suggest("es")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "error",
    [LLMNotConfiguredError("no key"), LLMBudgetExceeded("limit"), LLMError("boom")],
)
async def test_route_returns_empty_list_for_every_llm_error(error: LLMError) -> None:
    """The endpoint never surfaces a failure — the frontend has a fallback."""

    class RaisingLLM:
        enabled = True

        async def complete_json(self, **kwargs: object) -> dict[str, object]:
            raise error

    request = _MiniRequest(BiblePassageSuggester(RaisingLLM()))  # type: ignore[arg-type]
    assert await example_passages(request, "es") == []  # type: ignore[arg-type]


async def test_route_defaults_unknown_language_to_spanish() -> None:
    llm = FakeLLM(result={"passages": ["Romanos 8:31-39"]})
    request = _MiniRequest(BiblePassageSuggester(llm))

    assert await example_passages(request, "klingon") == ["Romanos 8:31-39"]  # type: ignore[arg-type]
    assert "es" in llm.calls[0]["system"].lower() or "Español" in llm.calls[0]["system"]


async def test_route_returns_empty_when_suggester_not_wired() -> None:
    request = _MiniRequest(None)
    assert await example_passages(request, "es") == []  # type: ignore[arg-type]


def test_endpoint_returns_200_and_a_list(client_factory: ClientFactory) -> None:
    """End-to-end through the app: always 200 with a JSON array."""
    llm = FakeLLM(result={"passages": ["Romanos 8:31-39", "bad book 1:1"]})
    with client_factory(llm=llm) as client:
        response = client.get("/api/bible/example-passages", params={"language": "es"})
        assert response.status_code == 200
        assert response.json() == ["Romanos 8:31-39"]


def test_endpoint_is_not_rate_limited(client_factory: ClientFactory) -> None:
    """A burst of language switches must not spend the study rate budget."""
    llm = FakeLLM(result={"passages": ["Salmos 23"]})
    with client_factory(llm=llm) as client:
        codes = [
            client.get("/api/bible/example-passages", params={"language": lang}).status_code
            for lang in ["es", "en", "pt"] * 15
        ]
    # 45 > RATE_LIMIT_PER_MINUTE (30): a rate-limited route would 429 here.
    assert set(codes) == {200}


def test_endpoint_degrades_to_empty_list_when_llm_unconfigured(
    client_factory: ClientFactory,
) -> None:
    with client_factory(llm=FakeLLM(enabled=False)) as client:
        response = client.get("/api/bible/example-passages")
        assert response.status_code == 200
        assert response.json() == []


def test_parse_reference_rejects_what_the_route_drops() -> None:
    """Guard the contract from the other side."""
    with pytest.raises(BibleReferenceError):
        parse_reference("NoExisteLibro 3:1")
