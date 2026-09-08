"""Tests for the LLM grammar-drill service."""

import pytest

from app.services.grammar_drill import GrammarDrillService
from app.services.llm import LLMError, LLMNotConfiguredError
from tests.backend.helpers import FakeLLM

_CLOZE = {
    "sentence": "We need to ___ the risk before committing.",
    "options": ["rule out", "run out", "rule in", "run in"],
    "answer": "rule out",
    "explanation": "'Rule out' means to eliminate a possibility.",
}


async def test_drill_returns_cloze() -> None:
    result = await GrammarDrillService(FakeLLM(result=_CLOZE)).drill("phrasal_verb")
    assert result.sentence == _CLOZE["sentence"]
    assert result.answer == "rule out"
    assert len(result.options) == 4


async def test_drill_rejects_answer_not_in_options() -> None:
    bad = dict(_CLOZE, answer="not an option")
    with pytest.raises(LLMError):
        await GrammarDrillService(FakeLLM(result=bad)).drill("collocation")


async def test_drill_truncates_to_four_options() -> None:
    five = dict(_CLOZE, options=["a", "b", "c", "d", "e"], answer="a")
    result = await GrammarDrillService(FakeLLM(result=five)).drill("use_of_english")
    assert len(result.options) == 4


async def test_word_forms_returns_drill() -> None:
    llm = FakeLLM(
        result={
            "sentence": "The ___ was final.",
            "root": "decide",
            "answer": "decision",
            "explanation": "Use the noun form.",
        }
    )
    result = await GrammarDrillService(llm).word_forms()
    assert result.root == "decide"
    assert result.answer == "decision"


async def test_coach_returns_answer() -> None:
    llm = FakeLLM(result={"answer": "Use the present perfect for relevance to now."})
    result = await GrammarDrillService(llm).coach("When do I use the present perfect?")
    assert result.answer


async def test_not_configured_raises() -> None:
    service = GrammarDrillService(FakeLLM(enabled=False))
    with pytest.raises(LLMNotConfiguredError):
        await service.drill("phrasal_verb")


async def test_malformed_raises() -> None:
    service = GrammarDrillService(FakeLLM(result={"sentence": 123}))
    with pytest.raises(LLMError):
        await service.drill("phrasal_verb")
