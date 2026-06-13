"""Bridge LangGraph agents into FastAPI services."""

from __future__ import annotations

import structlog

log = structlog.get_logger()


async def run_grade_roi_agent(*, card_id: str, psa_high: int) -> dict[str, object] | None:
    """Run GradeROIAgent graph; returns output dict or None on failure."""
    try:
        from tcgscan_agents.grade_roi_agent.graph import GradeROIInput, build_grade_roi_graph

        graph = build_grade_roi_graph().compile()
        state = await graph.ainvoke(
            {
                "input": GradeROIInput(card_id=card_id, psa_high=psa_high),
                "output": None,
            }
        )
        out = state.get("output")
        if out is None:
            return None
        return {
            "action": out.action,
            "reason": out.reason,
            "expected_profit_usd": out.expected_profit_usd,
        }
    except Exception as exc:
        log.warning("agents.grade_roi_failed", error=str(exc))
        return None
