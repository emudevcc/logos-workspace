"""Tests for the curated grammar rules."""

from datetime import date

from app.services.grammar_rules import RULE_COUNT, list_rules, rule_for_date


def test_rules_non_empty() -> None:
    assert RULE_COUNT >= 8


def test_each_rule_is_complete() -> None:
    for rule in list_rules():
        assert rule.id
        assert rule.title
        assert rule.rule
        assert len(rule.examples) >= 2
        assert rule.common_error


def test_rule_for_date_is_stable() -> None:
    day = date(2025, 3, 10)
    first = rule_for_date(day)
    second = rule_for_date(day)
    assert first.id == second.id


def test_rule_for_date_rotates_within_bounds() -> None:
    day = date(2025, 1, 1)
    rule = rule_for_date(day)
    assert any(rule.id == other.id for other in list_rules())
