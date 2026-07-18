from __future__ import annotations

import pytest
from structlog.testing import capture_logs

from tcgscan_agents.budget import BudgetExceededError, BudgetGuard
from tcgscan_agents.tracing import traced


def test_traced_success_logs_debug_start_and_end() -> None:
    @traced("demo_ok")
    def ok() -> str:
        return "ok"

    with capture_logs() as cap:
        assert ok() == "ok"

    events = [(e["event"], e["log_level"]) for e in cap]
    assert ("agent.node.start", "debug") in events
    assert ("agent.node.end", "debug") in events
    assert not any(e["event"] == "agent.node.failed" for e in cap)
    end = next(e for e in cap if e["event"] == "agent.node.end")
    assert end["node"] == "demo_ok"
    assert end["status"] == "ok"
    assert isinstance(end["duration_ms"], float)
    assert end["duration_ms"] >= 0


def test_traced_failure_logs_error_and_reraises() -> None:
    @traced("demo_fail")
    def boom() -> None:
        raise ValueError("nope")

    with capture_logs() as cap:
        with pytest.raises(ValueError, match="nope"):
            boom()

    assert not any(e["event"] == "agent.node.end" for e in cap)
    failed = next(e for e in cap if e["event"] == "agent.node.failed")
    assert failed["log_level"] == "error"
    assert failed["node"] == "demo_fail"
    assert failed["exc_type"] == "ValueError"
    assert isinstance(failed["duration_ms"], float)
    assert failed["duration_ms"] >= 0


@pytest.mark.parametrize(
    ("kwargs", "limit_type", "limit", "actual"),
    [
        ({"input_tokens": 10}, "input_tokens", 5, 10),
        ({"output_tokens": 10}, "output_tokens", 5, 10),
        ({"cost_usd": 1.0}, "cost_usd", 0.5, 1.0),
    ],
)
def test_budget_guard_logs_warning_before_raise(
    kwargs: dict[str, int | float],
    limit_type: str,
    limit: int | float,
    actual: int | float,
) -> None:
    guard = BudgetGuard(max_input_tokens=5, max_output_tokens=5, max_cost_usd=0.5)
    with capture_logs() as cap:
        with pytest.raises(BudgetExceededError):
            guard.record(**kwargs)

    warning = next(e for e in cap if e["event"] == "agent.budget_exceeded")
    assert warning["log_level"] == "warning"
    assert warning["limit_type"] == limit_type
    assert warning["limit"] == limit
    assert warning["actual"] == actual
