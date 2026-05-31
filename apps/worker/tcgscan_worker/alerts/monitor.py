"""Evaluate active price alerts via MonitorAgent graph."""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from sqlalchemy import select, update

from tcgscan_agents.monitor_agent.graph import MonitorInput, build_monitor_graph
from tcgscan_worker.db_bridge import session_scope

log = structlog.get_logger()

_monitor_graph = build_monitor_graph().compile()


async def evaluate_all_alerts() -> int:
    """Return count of triggered alerts."""
    from tcgscan_api.db.models import PriceAlert

    triggered = 0
    async with session_scope() as session:
        stmt = select(PriceAlert).where(PriceAlert.active.is_(True))
        alerts = list((await session.execute(stmt)).scalars().all())
        for alert in alerts:
            direction = alert.direction
            dir_val = direction.value if hasattr(direction, "value") else str(direction)
            state = await _monitor_graph.ainvoke(
                {
                    "input": MonitorInput(
                        alert_id=str(alert.id),
                        card_id=str(alert.card_id),
                        direction=dir_val,
                        threshold_usd=float(alert.threshold_usd),
                    ),
                    "output": None,
                }
            )
            out = state.get("output")
            if out is None or not out.triggered:
                continue
            triggered += 1
            await session.execute(
                update(PriceAlert)
                .where(PriceAlert.id == alert.id)
                .values(last_triggered_at=datetime.now(UTC))
            )
            log.info(
                "alert.triggered",
                alert_id=str(alert.id),
                card_id=str(alert.card_id),
                median=out.current_median_usd,
                threshold=float(alert.threshold_usd),
            )
        await session.commit()
    return triggered
