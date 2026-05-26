from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, StateGraph

from tcgscan_agents.budget import BudgetGuard
from tcgscan_agents.scan_agent.models import ScanAgentInput, ScanAgentOutput
from tcgscan_agents.tracing import traced


class ScanState(TypedDict):
    input: ScanAgentInput
    output: ScanAgentOutput | None


@traced("agent.scan.detect_stub")
def detect_stub(state: ScanState) -> ScanState:
    budget = BudgetGuard(max_cost_usd=0.01)
    budget.record(input_tokens=10, output_tokens=5, cost_usd=0.001)
    return {
        **state,
        "output": ScanAgentOutput(card_id=None, confidence=0.0),
    }


def build_scan_graph() -> StateGraph:
    g: StateGraph = StateGraph(ScanState)
    g.add_node("detect_stub", detect_stub)
    g.set_entry_point("detect_stub")
    g.add_edge("detect_stub", END)
    return g
