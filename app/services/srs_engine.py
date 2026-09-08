"""Pure SuperMemo SM-2 spaced-repetition engine.

Implements the original SM-2 schedule with the standard Ease Factor floor of
1.3. This module is deliberately free of I/O, clocks, and persistence so it can
be unit-tested exhaustively and reused unchanged by the API layer.
"""

from __future__ import annotations

from dataclasses import dataclass

# UI grading buttons -> SM-2 recall quality (0..5).
GRADE_TO_QUALITY: dict[int, int] = {
    1: 0,  # Again
    2: 3,  # Hard
    3: 4,  # Good
    4: 5,  # Easy
}

MIN_EASE_FACTOR: float = 1.3
INITIAL_EASE_FACTOR: float = 2.5
FIRST_INTERVAL_DAYS: int = 1
SECOND_INTERVAL_DAYS: int = 6
VALID_GRADES: frozenset[int] = frozenset(GRADE_TO_QUALITY)


class SrsEngineError(ValueError):
    """Raised when SM-2 inputs fall outside the accepted domain."""


@dataclass(frozen=True, slots=True)
class ReviewOutcome:
    """The new scheduling state produced by a single SM-2 review."""

    grade: int
    quality: int
    ease_factor: float
    interval_days: int
    repetitions: int


def grade_to_quality(grade: int) -> int:
    """Map a 1-4 UI grade to an SM-2 quality score (0..5)."""
    if grade not in VALID_GRADES:
        raise SrsEngineError(f"Grade must be one of {sorted(VALID_GRADES)}, got {grade}.")
    return GRADE_TO_QUALITY[grade]


def next_ease_factor(ease_factor: float, quality: int) -> float:
    """Apply the SM-2 E-Factor update, flooring the result at ``MIN_EASE_FACTOR``."""
    if ease_factor < MIN_EASE_FACTOR:
        raise SrsEngineError(f"ease_factor must be >= {MIN_EASE_FACTOR}, got {ease_factor}.")
    if not 0 <= quality <= 5:
        raise SrsEngineError(f"quality must be in 0..5, got {quality}.")

    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    return max(MIN_EASE_FACTOR, ease_factor + delta)


def next_repetition(
    *,
    ease_factor: float,
    interval_days: int,
    repetitions: int,
    grade: int,
) -> ReviewOutcome:
    """Schedule the next review for a card given a UI grade.

    A failed recall (quality < 3) restarts the repetition ladder without
    changing the E-Factor, exactly as the original SM-2 description specifies.
    """
    quality = grade_to_quality(grade)
    if ease_factor < MIN_EASE_FACTOR:
        raise SrsEngineError(f"ease_factor must be >= {MIN_EASE_FACTOR}, got {ease_factor}.")
    if interval_days < 0:
        raise SrsEngineError(f"interval_days must be >= 0, got {interval_days}.")
    if repetitions < 0:
        raise SrsEngineError(f"repetitions must be >= 0, got {repetitions}.")

    if quality < 3:
        return ReviewOutcome(
            grade=grade,
            quality=quality,
            ease_factor=ease_factor,
            interval_days=FIRST_INTERVAL_DAYS,
            repetitions=0,
        )

    new_ease = next_ease_factor(ease_factor, quality)
    if repetitions == 0:
        new_interval = FIRST_INTERVAL_DAYS
    elif repetitions == 1:
        new_interval = SECOND_INTERVAL_DAYS
    else:
        new_interval = max(FIRST_INTERVAL_DAYS, round(interval_days * new_ease))

    return ReviewOutcome(
        grade=grade,
        quality=quality,
        ease_factor=new_ease,
        interval_days=new_interval,
        repetitions=repetitions + 1,
    )
