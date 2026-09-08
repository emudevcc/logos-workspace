"""Unit tests for the pure SM-2 engine."""

import pytest

from app.services.srs_engine import (
    GRADE_TO_QUALITY,
    MIN_EASE_FACTOR,
    SrsEngineError,
    grade_to_quality,
    next_ease_factor,
    next_repetition,
)


def test_grade_mapping_table_is_exact() -> None:
    assert GRADE_TO_QUALITY == {1: 0, 2: 3, 3: 4, 4: 5}


def test_grade_to_quality_rejects_unknown_grade() -> None:
    with pytest.raises(SrsEngineError):
        grade_to_quality(0)
    with pytest.raises(SrsEngineError):
        grade_to_quality(5)


def test_first_good_review_schedules_one_day() -> None:
    outcome = next_repetition(ease_factor=2.5, interval_days=0, repetitions=0, grade=3)
    assert outcome.interval_days == 1
    assert outcome.repetitions == 1
    assert outcome.ease_factor == pytest.approx(2.5)


def test_second_good_review_schedules_six_days() -> None:
    outcome = next_repetition(ease_factor=2.5, interval_days=1, repetitions=1, grade=3)
    assert outcome.interval_days == 6
    assert outcome.repetitions == 2


def test_third_review_multiplies_interval_by_ease_factor() -> None:
    outcome = next_repetition(ease_factor=2.5, interval_days=6, repetitions=2, grade=3)
    assert outcome.interval_days == 15  # round(6 * 2.5)
    assert outcome.repetitions == 3


def test_easy_grade_increases_ease_factor() -> None:
    outcome = next_repetition(ease_factor=2.5, interval_days=6, repetitions=2, grade=4)
    assert outcome.ease_factor == pytest.approx(2.6)
    assert outcome.interval_days == 16  # round(6 * 2.6)


def test_hard_grade_decreases_ease_factor_without_reset() -> None:
    outcome = next_repetition(ease_factor=2.5, interval_days=6, repetitions=2, grade=2)
    assert outcome.ease_factor == pytest.approx(2.36)
    assert outcome.repetitions == 3


def test_again_grade_resets_repetitions_and_keeps_ease_factor() -> None:
    outcome = next_repetition(ease_factor=2.36, interval_days=15, repetitions=3, grade=1)
    assert outcome.repetitions == 0
    assert outcome.interval_days == 1
    assert outcome.ease_factor == pytest.approx(2.36)


def test_ease_factor_is_floored_at_1_3() -> None:
    assert next_ease_factor(1.4, quality=3) == pytest.approx(MIN_EASE_FACTOR)


def test_next_ease_factor_rejects_quality_out_of_range() -> None:
    with pytest.raises(SrsEngineError):
        next_ease_factor(2.5, quality=6)
    with pytest.raises(SrsEngineError):
        next_ease_factor(2.5, quality=-1)


def test_next_repetition_rejects_bad_state() -> None:
    with pytest.raises(SrsEngineError):
        next_repetition(ease_factor=1.0, interval_days=0, repetitions=0, grade=3)
    with pytest.raises(SrsEngineError):
        next_repetition(ease_factor=2.5, interval_days=-1, repetitions=0, grade=3)
    with pytest.raises(SrsEngineError):
        next_repetition(ease_factor=2.5, interval_days=0, repetitions=-1, grade=3)
