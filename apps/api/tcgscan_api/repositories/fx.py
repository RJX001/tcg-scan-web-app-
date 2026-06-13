from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tcgscan_api.db.models import FxRate


class FxRepo:
    """USD-base FX rates (`fx_rate`): rate_to_usd = value of 1 unit in USD."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def latest_rates(self) -> tuple[datetime | None, dict[str, float]]:
        """Most recent rate per currency, plus the newest as-of day."""
        latest = (
            select(FxRate.currency, func.max(FxRate.day).label("day"))
            .group_by(FxRate.currency)
            .subquery()
        )
        stmt = select(FxRate).join(
            latest, (FxRate.currency == latest.c.currency) & (FxRate.day == latest.c.day)
        )
        rows = list((await self._session.execute(stmt)).scalars().all())
        if not rows:
            return None, {}
        as_of = max(r.day for r in rows)
        return as_of, {r.currency: float(r.rate_to_usd) for r in rows}

    async def upsert_many(self, *, day: datetime, rates_to_usd: dict[str, float]) -> int:
        for currency, rate in rates_to_usd.items():
            await self._session.merge(FxRate(day=day, currency=currency.upper(), rate_to_usd=rate))
        await self._session.commit()
        return len(rates_to_usd)
