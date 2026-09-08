"""Internal content-calibration blend for ALL generated practice content.

There is deliberately no user-facing level system: every item the app produces
is calibrated to be *mostly elementary English (A1–A2)* with an occasional
clearer intermediate item (B1–B2), so a beginner never drowns but still meets a
slightly harder sentence now and then to grow into. The blend is weighted
randomly per item (about 4 in 5 easy, 1 in 5 intermediate).
"""

from __future__ import annotations

import random
from collections.abc import Callable

_EASY_GUIDANCE = (
    "very simple, elementary English (A1–A2): short everyday sentences of 5–10 "
    "words, high-frequency vocabulary, present and past simple only, no idioms."
)

_MID_GUIDANCE = (
    "clear everyday English (B1–B2): short sentences of 8–14 words, common "
    "vocabulary and everyday topics, standard tenses, at most one very common idiom."
)

# ~80% elementary, ~20% intermediate so content reads beginner-first.
_MID_PROBABILITY = 0.2


def calibration_guidance(rng: Callable[[], float] = random.random) -> str:
    """Prompt text telling the LLM how simple the current item should be."""
    if rng() < _MID_PROBABILITY:
        return _MID_GUIDANCE
    return _EASY_GUIDANCE
