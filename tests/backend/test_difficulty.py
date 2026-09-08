"""Tests for the internal beginner-first calibration blend."""

from __future__ import annotations

from app.services.difficulty import calibration_guidance


def test_low_draw_serves_the_occasional_intermediate_item() -> None:
    # ~20% of draws land on the B1–B2 guidance (the "some B1–B2" part).
    assert "B1–B2" in calibration_guidance(lambda: 0.01)


def test_high_draw_serves_elementary_guidance() -> None:
    # The remaining ~80% of draws are the elementary A1–A2 guidance.
    assert "A1–A2" in calibration_guidance(lambda: 0.99)


def test_guidance_never_mentions_levels() -> None:
    for draw in (0.01, 0.5, 0.99):
        fixed = calibration_guidance(lambda value=draw: value)
        assert "level" not in fixed.lower()
