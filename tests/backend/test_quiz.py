"""Tests for the comprehension-quiz service and endpoint."""

from typing import Any

import pytest

from app.services.llm import LLMError, LLMNotConfiguredError
from app.services.quiz import QuizService
from tests.backend.helpers import ClientFactory, FakeLLM


def _result() -> dict[str, Any]:
    return {"question": "What happened?", "correct_answer": "A", "distractors": ["B", "C", "D"]}


async def test_quiz_generates_item() -> None:
    item = await QuizService(FakeLLM(result=_result())).generate("Some text")
    assert item.question == "What happened?"
    assert item.correct_answer == "A"
    assert len(item.distractors) == 3


async def test_quiz_not_configured_raises() -> None:
    with pytest.raises(LLMNotConfiguredError):
        await QuizService(FakeLLM(enabled=False)).generate("text")


async def test_quiz_malformed_raises() -> None:
    with pytest.raises(LLMError):
        await QuizService(FakeLLM(result={"question": "Q"})).generate("text")


def test_quiz_endpoint(client_factory: ClientFactory) -> None:
    llm = FakeLLM(result=_result())
    with client_factory(llm=llm) as client:
        response = client.post("/api/quiz", json={"text": "Some headline"})
        assert response.status_code == 200
        assert response.json()["question"] == "What happened?"
