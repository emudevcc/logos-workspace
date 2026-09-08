"""Tests for the LLM shadowing-sentence service."""

from __future__ import annotations

import pytest

from app.services.llm import LLMNotConfiguredError
from app.services.shadowing import ShadowingService
from tests.backend.helpers import FakeLLM


class SequenceLLM(FakeLLM):
    """FakeLLM that returns each canned result in turn."""

    def __init__(self, results: list[dict[str, str]]) -> None:
        super().__init__(results[0] if results else {})
        self._results = list(results)
        self.attempts = 0

    async def complete_json(self, **_: object) -> dict[str, object]:
        self.attempts += 1
        result = self._results[min(self.attempts - 1, len(self._results) - 1)]
        return dict(result)


async def test_random_sentence_returns_text() -> None:
    llm = FakeLLM(result={"sentence": "I drink coffee every morning."})
    service = ShadowingService(llm)
    assert await service.random_sentence() == "I drink coffee every morning."


async def test_random_sentence_is_calibrated_to_the_blend() -> None:
    # The system prompt must always carry the elementary/intermediate
    # calibration guidance, never a user-facing level label.
    llm = FakeLLM(result={"sentence": "The dog is sleeping."})
    service = ShadowingService(llm)
    await service.random_sentence()
    assert "Calibration:" in llm.calls[0]["system"]
    assert "Level" not in llm.calls[0]["system"]


async def test_random_sentence_retries_recent_repeats() -> None:
    llm = SequenceLLM(
        [{"sentence": "Repeat me."}, {"sentence": "Repeat me."}, {"sentence": "Brand new phrase."}]
    )
    service = ShadowingService(llm)
    first = await service.random_sentence()
    second = await service.random_sentence()
    assert first == "Repeat me."
    assert second == "Brand new phrase."
    assert llm.attempts == 3


async def test_random_sentence_not_configured_raises() -> None:
    service = ShadowingService(FakeLLM(enabled=False))
    with pytest.raises(LLMNotConfiguredError):
        await service.random_sentence()
