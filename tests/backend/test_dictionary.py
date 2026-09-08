"""Tests for the click-to-translate dictionary service and endpoint."""

from typing import Any

import pytest

from app.services.dictionary import DictionaryService
from app.services.llm import LLMError, LLMNotConfiguredError
from tests.backend.helpers import ClientFactory, FakeLLM


def _result() -> dict[str, Any]:
    return {
        "ipa": "/ˈhɛloʊ/",
        "part_of_speech": "noun",
        "synonyms": ["greeting", "salutation"],
        "spanish": "hola",
        "example": "She said hello to everyone.",
    }


async def test_lookup_returns_parsed_result() -> None:
    llm = FakeLLM(result=_result())
    service = DictionaryService(llm)
    result = await service.lookup("Hello")
    assert result.word == "Hello"  # original case preserved for display
    assert result.ipa == "/ˈhɛloʊ/"
    assert result.synonyms == ["greeting", "salutation"]
    assert result.spanish == "hola"


async def test_lookup_handles_phrase() -> None:
    llm = FakeLLM(result=_result())
    service = DictionaryService(llm)
    result = await service.lookup("look forward to")
    assert result.word == "look forward to"
    assert llm.calls[0]["user"] == "look forward to"


async def test_lookup_is_cached_case_insensitively() -> None:
    llm = FakeLLM(result=_result())
    service = DictionaryService(llm)
    await service.lookup("Hello")
    await service.lookup("hello")
    assert len(llm.calls) == 1


async def test_lookup_not_configured_raises() -> None:
    service = DictionaryService(FakeLLM(enabled=False))
    with pytest.raises(LLMNotConfiguredError):
        await service.lookup("hello")


async def test_lookup_malformed_raises() -> None:
    service = DictionaryService(FakeLLM(result={"ipa": "x"}))
    with pytest.raises(LLMError):
        await service.lookup("hello")


def test_dictionary_endpoint(client_factory: ClientFactory) -> None:
    llm = FakeLLM(
        result={
            "ipa": "/x/",
            "part_of_speech": "noun",
            "synonyms": ["s"],
            "spanish": "hola",
            "example": "e",
        }
    )
    with client_factory(llm=llm) as client:
        response = client.get("/api/dictionary/lookup", params={"word": "hello"})
        assert response.status_code == 200
        assert response.json()["spanish"] == "hola"
