from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, StateGraph
from pydantic import BaseModel

from tcgscan_agents.tools.pricing import fetch_active_listings, fetch_comps_summary
from tcgscan_agents.tracing import traced


class PricingInput(BaseModel):
    card_id: str
    days: int = 30


class PricingOutput(BaseModel):
    card_id: str
    summary: dict[str, object]
    active_listings: list[dict[str, object]]


class PricingState(TypedDict):
    input: PricingInput
    output: PricingOutput | None


@traced("agent.pricing.fetch")
async def fetch_node(state: PricingState) -> PricingState:
    inp = state["input"]
    summary = await fetch_comps_summary(inp.card_id, days=inp.days)
    listings = await fetch_active_listings(inp.card_id)
    return {
        **state,
        "output": PricingOutput(
            card_id=inp.card_id,
            summary=summary,
            active_listings=listings,
        ),
    }


def build_pricing_graph() -> Any:
    g = StateGraph(PricingState)
    g.add_node("fetch", fetch_node)
    g.set_entry_point("fetch")
    g.add_edge("fetch", END)
    return g
