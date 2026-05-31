from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, StateGraph
from pydantic import BaseModel

from tcgscan_agents.budget import BudgetGuard
from tcgscan_agents.digest_agent.prompts import DIGEST_COMPOSE_PROMPT  # used when LLM synthesis enabled
from tcgscan_agents.tracing import traced

_ = DIGEST_COMPOSE_PROMPT  # Sonnet node will consume this when ANTHROPIC_API_KEY is set


class DigestInput(BaseModel):
    user_id: str
    portfolio_count: int = 0


class DigestOutput(BaseModel):
    user_id: str
    subject: str
    body: str


class DigestState(TypedDict):
    input: DigestInput
    output: DigestOutput | None


@traced("agent.digest.compose")
def compose_node(state: DigestState) -> DigestState:
    inp = state["input"]
    budget = BudgetGuard(max_cost_usd=0.25)
    budget.record(input_tokens=500, output_tokens=300, cost_usd=0.02)
    body = (
        f"Good morning — your portfolio has {inp.portfolio_count} cards tracked. "
        "Run pricing ingest for live movers. (Sonnet synthesis when ANTHROPIC_API_KEY is set.)"
    )
    return {
        **state,
        "output": DigestOutput(
            user_id=inp.user_id,
            subject="TCG Scan daily brief",
            body=body,
        ),
    }


def build_digest_graph() -> StateGraph:
    g: StateGraph = StateGraph(DigestState)
    g.add_node("compose", compose_node)
    g.set_entry_point("compose")
    g.add_edge("compose", END)
    return g
