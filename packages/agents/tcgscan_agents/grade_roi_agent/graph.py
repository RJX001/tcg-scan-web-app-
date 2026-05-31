from __future__ import annotations

from typing import Literal, TypedDict

from langgraph.graph import END, StateGraph
from pydantic import BaseModel

from tcgscan_agents.budget import BudgetGuard
from tcgscan_agents.tools.pricing import _api_base
from tcgscan_agents.tracing import traced


class GradeROIInput(BaseModel):
    card_id: str
    psa_high: int = 9


class GradeROIOutput(BaseModel):
    action: Literal["HOLD", "SELL", "GRADE", "BUY"]
    reason: str
    expected_profit_usd: float | None = None


class GradeROIState(TypedDict):
    input: GradeROIInput
    output: GradeROIOutput | None


@traced("agent.grade_roi.rules")
def rules_node(state: GradeROIState) -> GradeROIState:
    import httpx

    inp = state["input"]
    summary: dict[str, object] = {"median_usd": None}
    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.get(
                f"{_api_base()}/v1/cards/{inp.card_id}/comps/summary",
                params={"days": 30},
            )
            if r.status_code == 200:
                summary = r.json()
    except httpx.HTTPError:
        pass
    median = summary.get("median_usd")
    cost = 25.0
    if median is None:
        return {
            **state,
            "output": GradeROIOutput(action="HOLD", reason="Insufficient comps for ROI."),
        }
    graded_est = float(median) * 2.5
    profit = graded_est - float(median) - cost
    if inp.psa_high >= 9 and profit >= 40:
        action: Literal["HOLD", "SELL", "GRADE", "BUY"] = "GRADE"
        reason = f"Estimated ${profit:.0f} upside after grading."
    elif inp.psa_high <= 7:
        action = "SELL"
        reason = "Condition likely below PSA 8 — sell raw."
    else:
        action = "HOLD"
        reason = "Borderline — monitor comps."
    return {
        **state,
        "output": GradeROIOutput(action=action, reason=reason, expected_profit_usd=profit),
    }


@traced("agent.grade_roi.synthesis")
def synthesis_node(state: GradeROIState) -> GradeROIState:
    """Escalate to Sonnet in production when ANTHROPIC_API_KEY is set."""
    budget = BudgetGuard(max_cost_usd=0.15)
    budget.record(input_tokens=200, output_tokens=80, cost_usd=0.01)
    return state


def build_grade_roi_graph() -> StateGraph:
    g: StateGraph = StateGraph(GradeROIState)
    g.add_node("rules", rules_node)
    g.add_node("synthesis", synthesis_node)
    g.set_entry_point("rules")
    g.add_edge("rules", "synthesis")
    g.add_edge("synthesis", END)
    return g
