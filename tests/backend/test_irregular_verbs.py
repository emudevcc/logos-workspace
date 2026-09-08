"""Tests for the curated irregular-verbs data."""

from app.services.irregular_verbs import IRREGULAR_VERBS, all_irregular_verbs


def test_verbs_are_non_empty() -> None:
    assert len(IRREGULAR_VERBS) >= 100


def test_each_verb_has_three_forms() -> None:
    for verb in IRREGULAR_VERBS:
        assert verb.base
        assert verb.past
        assert verb.participle


def test_all_irregular_verbs_returns_copy() -> None:
    assert all_irregular_verbs() == list(IRREGULAR_VERBS)
