from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from tcgscan_agents.budget import BudgetGuard
from tcgscan_agents.scan_agent.models import ScanAgentInput, ScanAgentOutput
from tcgscan_agents.tools.pricing import fetch_comps_summary
from tcgscan_agents.tracing import traced


class ScanState(TypedDict):
    input: ScanAgentInput
    output: ScanAgentOutput | None
    comps: dict[str, object] | None


@traced("agent.scan.match")
def match_node(state: ScanState) -> ScanState:
    budget = BudgetGuard(max_cost_usd=0.05)
    budget.record(input_tokens=50, output_tokens=20, cost_usd=0.002)
    # Production: call ML + Qdrant via apps/api run_scan
    return {
        **state,
        "output": ScanAgentOutput(card_id=None, confidence=0.0),
    }


@traced("agent.scan.pricing")
async def pricing_node(state: ScanState) -> ScanState:
    out = state.get("output")
    if out and out.card_id:
        comps = await fetch_comps_summary(out.card_id)
        return {**state, "comps": comps}
    return state


def build_scan_graph() -> Any:
    g = StateGraph(ScanState)
    g.add_node("match", match_node)
    g.add_node("pricing", pricing_node)
    g.set_entry_point("match")
    g.add_edge("match", "pricing")
    g.add_edge("pricing", END)
    return g
