import pytest

from tcgscan_agents.budget import BudgetExceededError, BudgetGuard


def test_budget_guard_allows_under_limit() -> None:
    b = BudgetGuard(max_cost_usd=1.0)
    b.record(cost_usd=0.5)


def test_budget_guard_raises() -> None:
    b = BudgetGuard(max_cost_usd=0.01)
    with pytest.raises(BudgetExceededError):
        b.record(cost_usd=0.02)
