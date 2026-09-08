"""Tests for the speaking-monologue service."""

import pytest

from app.services.llm import LLMNotConfiguredError
from app.services.monologue import MonologueService
from tests.backend.helpers import FakeLLM


def test_topics_are_non_empty() -> None:
    topics = MonologueService(FakeLLM()).topics()
    assert len(topics) >= 6
    assert all(topic for topic in topics)


async def test_evaluate_returns_scores() -> None:
    llm = FakeLLM(
        result={
            "structure_score": 70,
            "fluency_score": 65,
            "vocabulary_score": 80,
            "grammar_score": 75,
            "strengths": ["Clear opening"],
            "improvements": ["Cut fillers"],
            "model_answer": "A model answer.",
        }
    )
    result = await MonologueService(llm).evaluate("Topic", "I spoke.", 60.0)
    assert result.structure_score == 70
    assert result.strengths == ["Clear opening"]
    assert result.model_answer == "A model answer."


async def test_evaluate_clamps_scores() -> None:
    llm = FakeLLM(
        result={
            "structure_score": 999,
            "fluency_score": -3,
            "vocabulary_score": 50,
            "grammar_score": 50,
            "strengths": [],
            "improvements": [],
            "model_answer": "",
        }
    )
    result = await MonologueService(llm).evaluate("Topic", "I spoke.", 60.0)
    assert result.structure_score == 100
    assert result.fluency_score == 0


async def test_evaluate_not_configured_raises() -> None:
    service = MonologueService(FakeLLM(enabled=False))
    with pytest.raises(LLMNotConfiguredError):
        await service.evaluate("Topic", "I spoke.", 60.0)
