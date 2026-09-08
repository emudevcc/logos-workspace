"""Tests for the daily spend budget."""

from app.core.budget import SpendBudget


def test_budget_limits_within_window() -> None:
    budget = SpendBudget(daily_limit=2)
    assert budget.consume() is True
    assert budget.consume() is True
    assert budget.consume() is False


def test_zero_limit_means_unlimited() -> None:
    budget = SpendBudget(daily_limit=0)
    for _ in range(100):
        assert budget.consume() is True
