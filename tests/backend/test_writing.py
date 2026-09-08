"""Tests for the writing-correct service."""

import pytest

from app.services.llm import LLMError, LLMNotConfiguredError
from app.services.writing import WritingCoachService
from tests.backend.helpers import FakeLLM


async def test_correct_returns_corrections() -> None:
    llm = FakeLLM(
        result={
            "corrected": "He goes to work every day.",
            "corrections": [
                {"original": "He go", "corrected": "He goes", "explanation": "3rd-person -s"}
            ],
        }
    )
    result = await WritingCoachService(llm).correct("He go to work every day.")
    assert result.corrected == "He goes to work every day."
    assert result.error_count == 1
    assert result.corrections[0].original == "He go"


async def test_correct_with_no_errors() -> None:
    llm = FakeLLM(result={"corrected": "All good.", "corrections": []})
    result = await WritingCoachService(llm).correct("All good.")
    assert result.error_count == 0
    assert result.corrections == []


async def test_correct_not_configured_raises() -> None:
    service = WritingCoachService(FakeLLM(enabled=False))
    with pytest.raises(LLMNotConfiguredError):
        await service.correct("hello")


async def test_correct_malformed_raises() -> None:
    service = WritingCoachService(FakeLLM(result={"corrected": 123}))
    with pytest.raises(LLMError):
        await service.correct("hello")
