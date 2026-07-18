"""FX rates for normalising marketplace comps to USD."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import structlog
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from tcgscan_api.db.models import FxRate

log = structlog.get_logger()

# Static dev rates — replace with daily ECB/API fetch in production.
DEFAULT_RATES: dict[str, Decimal] = {
    "USD": Decimal("1"),
    "EUR": Decimal("1.08"),
    "GBP": Decimal("1.27"),
}


async def ensure_fx_rates(session: AsyncSession, *, day: datetime | None = None) -> None:
    day = (day or datetime.now(timezone.utc)).replace(hour=0, minute=0, second=0, microsecond=0)
    dialect = session.bind.dialect.name if session.bind else "postgresql"
    for currency, rate in DEFAULT_RATES.items():
        if currency == "USD":
            continue
        row = {"day": day, "currency": currency, "rate_to_usd": rate}
        if dialect == "postgresql":
            stmt = pg_insert(FxRate).values(row)
            stmt = stmt.on_conflict_do_update(
                index_elements=["day", "currency"],
                set_={"rate_to_usd": stmt.excluded.rate_to_usd},
            )
            await session.execute(stmt)
        else:
            from sqlalchemy import select

            existing = (
                await session.execute(
                    select(FxRate).where(FxRate.day == day, FxRate.currency == currency)
                )
            ).scalar_one_or_none()
            if existing is None:
                session.add(FxRate(**row))
            else:
                existing.rate_to_usd = rate
    await session.commit()
    log.debug("fx.rates.ready", currencies=list(DEFAULT_RATES))


async def to_usd(
    session: AsyncSession, *, amount: Decimal, currency: str, day: datetime | None = None
) -> Decimal:
    cur = currency.upper()
    if cur == "USD":
        return amount
    day = (day or datetime.now(timezone.utc)).replace(hour=0, minute=0, second=0, microsecond=0)
    from sqlalchemy import select

    row = (
        await session.execute(
            select(FxRate.rate_to_usd).where(FxRate.day == day, FxRate.currency == cur)
        )
    ).scalar_one_or_none()
    rate = row if row is not None else DEFAULT_RATES.get(cur)
    if rate is None:
        log.error("fx.missing_rate", currency=cur)
        return amount
    return (amount * Decimal(rate)).quantize(Decimal("0.01"))
