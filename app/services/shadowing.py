"""Infinite shadowing/dictation sentences, LLM-generated on demand.

Each call returns a fresh English sentence so shadowing/dictation practice never
runs dry. Every sentence is calibrated to be *mostly elementary (A1–A2) with an
occasional clear intermediate (B1–B2)* — see ``difficulty.py`` — and is kept
from repeating recently-served sentences, so consecutive items vary in both
difficulty and phrasing instead of following an order.
"""

from __future__ import annotations

import random
from collections import deque

from pydantic import BaseModel, ConfigDict, ValidationError

from app.services.difficulty import calibration_guidance
from app.services.llm import LLMError, LLMProvider

_SYSTEM = (
    "You are an English drill generator for a Spanish-speaking beginner. "
    "Write ONE natural, simple English sentence (5–12 words) suitable for a "
    "shadowing or dictation exercise. Vary the topic and structure every time; "
    "never repeat phrasing from earlier answers. Respond ONLY with JSON: "
    '{"sentence": "string"}.'
)

# Everyday topics that stay within a beginner's world.
_TOPIC_CUES: tuple[str, ...] = (
    "a morning routine",
    "weekend plans",
    "going to the supermarket",
    "the weather today",
    "a simple phone call",
    "having coffee with a friend",
    "a pet",
    "the way to work or school",
    "what someone likes to eat",
    "buying something in a shop",
    "a family visit",
    "cleaning the house",
)

_RECENT_WINDOW = 6
_MAX_ATTEMPTS = 3


def _normalize(sentence: str) -> str:
    """Case/whitespace/punctuation-insensitive key used to catch repeats."""
    return " ".join(sentence.lower().strip(" .!?,;:\"'").split())


class _SentenceLLM(BaseModel):
    model_config = ConfigDict(extra="ignore")

    sentence: str


class ShadowingService:
    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm
        self._recent: deque[str] = deque(maxlen=_RECENT_WINDOW)

    async def random_sentence(self) -> str:
        """Return a fresh sentence calibrated to the beginner-first blend.

        The sentence is regenerated (up to a bounded number of attempts) if it
        duplicates a recently-served one, so the same sentence never comes back.
        """
        system = f"{_SYSTEM} Calibration: {calibration_guidance()}"
        user = f"Topic cue: {random.choice(_TOPIC_CUES)}."

        sentence = ""
        for _ in range(_MAX_ATTEMPTS):
            raw = await self._llm.complete_json(
                system=system, user=user, max_tokens=120, temperature=0.95
            )
            try:
                parsed = _SentenceLLM.model_validate(raw)
            except ValidationError as exc:
                raise LLMError(f"Shadow sentence validation failed: {exc}") from exc
            sentence = parsed.sentence
            if not self._seen_recently(parsed.sentence):
                break
        self._recent.append(sentence)
        return sentence

    def _seen_recently(self, sentence: str) -> bool:
        key = _normalize(sentence)
        return any(_normalize(seen) == key for seen in self._recent)
