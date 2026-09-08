"""Unit tests for the de-clutter service."""

import pytest

from app.schemas.assist import DeclutterRequest
from app.services.declutter import DeclutterService
from app.services.llm import LLMError, LLMNotConfiguredError
from tests.backend.helpers import FakeLLM


async def test_declutter_computes_word_reduction() -> None:
    llm = FakeLLM(
        result={
            "revised": "A short revised version.",
            "cut_phrases": ["in order to"],
            "verb_upgrades": [{"weak": "take into consideration", "strong": "evaluate"}],
            "tone": "Direct and confident.",
        }
    )
    service = DeclutterService(llm)
    result = await service.declutter(
        DeclutterRequest(
            draft="In order to take this into consideration for a much longer version of the draft."
        )
    )
    assert result.word_count_before > result.word_count_after
    assert result.reduction_pct > 0
    assert result.verb_upgrades[0].strong == "evaluate"


async def test_declutter_not_configured_raises() -> None:
    service = DeclutterService(FakeLLM(enabled=False))
    with pytest.raises(LLMNotConfiguredError):
        await service.declutter(DeclutterRequest(draft="hello"))


async def test_declutter_malformed_raises() -> None:
    service = DeclutterService(FakeLLM(result={"revised": 123}))
    with pytest.raises(LLMError):
        await service.declutter(DeclutterRequest(draft="hello"))
