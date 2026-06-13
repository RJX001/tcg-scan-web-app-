from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, StateGraph
from pydantic import BaseModel

from tcgscan_agents.tools.pricing import fetch_comps_summary
from tcgscan_agents.tracing import traced


class MonitorInput(BaseModel):
    alert_id: str
    card_id: str
    direction: str
    threshold_usd: float


class MonitorOutput(BaseModel):
    alert_id: str
    triggered: bool
    current_median_usd: float | None = None


class MonitorState(TypedDict):
    input: MonitorInput
    output: MonitorOutput | None


@traced("agent.monitor.evaluate")
async def evaluate_node(state: MonitorState) -> MonitorState:
    inp = state["input"]
    summary = await fetch_comps_summary(inp.card_id)
    median = summary.get("median_usd")
    triggered = False
    if median is not None:
        med_f = float(median)
        if inp.direction == "below" and med_f <= inp.threshold_usd:
            triggered = True
        if inp.direction == "above" and med_f >= inp.threshold_usd:
            triggered = True
    return {
        **state,
        "output": MonitorOutput(
            alert_id=inp.alert_id,
            triggered=triggered,
            current_median_usd=float(median) if median is not None else None,
        ),
    }


def build_monitor_graph() -> Any:
    g = StateGraph(MonitorState)
    g.add_node("evaluate", evaluate_node)
    g.set_entry_point("evaluate")
    g.add_edge("evaluate", END)
    return g
