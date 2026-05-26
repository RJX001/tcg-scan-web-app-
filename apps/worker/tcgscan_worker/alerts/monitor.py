"""Evaluate active price alerts against latest comps."""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from sqlalchemy import select, update

from tcgscan_worker.db_bridge import session_scope

log = structlog.get_logger()


async def evaluate_all_alerts() -> int:
    """Return count of triggered alerts."""
    from tcgscan_api.db.models import AlertDirection, PriceAlert
    from tcgscan_api.repositories.sales import SalesRepo

    triggered = 0
    async with session_scope() as session:
        stmt = select(PriceAlert).where(PriceAlert.active.is_(True))
        alerts = list((await session.execute(stmt)).scalars().all())
        for alert in alerts:
            summary = await SalesRepo(session).comps_for_card(alert.card_id, days=7)
            prices = [
                float(r.price_usd or r.price)
                for r in summary
                if r.price_usd is not None or r.currency == "USD"
            ]
            if not prices:
                continue
            prices.sort()
            median = prices[len(prices) // 2]
            direction = alert.direction
            dir_val = direction.value if hasattr(direction, "value") else str(direction)
            fire = False
            threshold = float(alert.threshold_usd)
            if dir_val == AlertDirection.below.value and median <= threshold:
                fire = True
            if dir_val == AlertDirection.above.value and median >= threshold:
                fire = True
            if fire:
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
                    median=median,
                    threshold=threshold,
                )
        await session.commit()
    return triggered
