"""Tests for the curated minimal-pairs and pitfalls data."""

from app.services.minimal_pairs import MINIMAL_PAIRS, SPANISH_PITFALLS


def test_pairs_are_non_empty() -> None:
    assert len(MINIMAL_PAIRS) >= 40


def test_each_pair_has_two_distinct_words_and_ipa() -> None:
    for pair in MINIMAL_PAIRS:
        assert pair.a and pair.b and pair.a != pair.b
        assert pair.ipa_a.startswith("/")
        assert pair.ipa_b.startswith("/")


def test_pitfalls_are_non_empty() -> None:
    assert len(SPANISH_PITFALLS) >= 8
    for pitfall in SPANISH_PITFALLS:
        assert pitfall.issue
        assert pitfall.tip
