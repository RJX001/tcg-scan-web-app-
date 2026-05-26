from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from tcgscan_api.db.models import CardPriceDaily, SaleEvent


class SalesRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_insert(self, rows: Iterable[dict[str, object]]) -> int:
        items = list(rows)
        if not items:
            return 0
        for r in items:
            r.setdefault("id", uuid.uuid4())

        dialect = self._session.bind.dialect.name if self._session.bind else "postgresql"
        if dialect == "postgresql":
            stmt = pg_insert(SaleEvent).values(items)
            stmt = stmt.on_conflict_do_nothing(constraint="uq_sale_dedup")
            await self._session.execute(stmt)
        else:
            for r in items:
                self._session.add(SaleEvent(**r))
        await self._session.commit()
        return len(items)

    async def comps_for_card(
        self,
        card_id: uuid.UUID,
        *,
        days: int = 30,
        source: str | None = None,
        grade: str | None = None,
    ) -> list[SaleEvent]:
        since = datetime.now() - timedelta(days=days)
        stmt = (
            select(SaleEvent)
            .where(SaleEvent.card_id == card_id, SaleEvent.sold_at >= since)
            .order_by(SaleEvent.sold_at.desc())
        )
        if source:
            stmt = stmt.where(SaleEvent.source == source)
        if grade:
            if grade.lower() == "raw":
                stmt = stmt.where(
                    (SaleEvent.grade.is_(None)) | (SaleEvent.grade.in_(["raw", "RAW", "None", ""]))
                )
            else:
                stmt = stmt.where(SaleEvent.grade.ilike(f"%{grade}%"))
        return list((await self._session.execute(stmt)).scalars().all())

    async def listings_for_card(
        self,
        card_id: uuid.UUID,
        *,
        limit: int = 20,
        source: str | None = None,
    ) -> list[SaleEvent]:
        from tcgscan_api.db.models import SaleKind

        stmt = (
            select(SaleEvent)
            .where(SaleEvent.card_id == card_id, SaleEvent.kind == SaleKind.listing)
            .order_by(SaleEvent.price_usd.asc().nullslast(), SaleEvent.sold_at.desc())
            .limit(limit)
        )
        if source:
            stmt = stmt.where(SaleEvent.source == source)
        return list((await self._session.execute(stmt)).scalars().all())

    async def chart_series(
        self, card_id: uuid.UUID, *, days: int = 90, grade_bucket: str = "raw"
    ) -> list[CardPriceDaily]:
        since = datetime.now() - timedelta(days=days)
        stmt = (
            select(CardPriceDaily)
            .where(
                CardPriceDaily.card_id == card_id,
                CardPriceDaily.grade_bucket == grade_bucket,
                CardPriceDaily.day >= since,
            )
            .order_by(CardPriceDaily.day.asc())
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def source_summary(
        self, card_id: uuid.UUID, *, days: int = 30
    ) -> dict[str, float]:
        """Median USD per source for price tiles."""
        since = datetime.now() - timedelta(days=days)
        stmt = (
            select(
                SaleEvent.source,
                func.percentile_cont(0.5).within_group(SaleEvent.price_usd.asc()),
            )
            .where(
                SaleEvent.card_id == card_id,
                SaleEvent.sold_at >= since,
                SaleEvent.price_usd.is_not(None),
            )
            .group_by(SaleEvent.source)
        )
        rows = (await self._session.execute(stmt)).all()
        return {str(src): float(med) for src, med in rows if med is not None}

    async def rollup_day(self, card_id: uuid.UUID, day: datetime) -> int:
        """Compute roll-ups per grade_bucket for a given (card_id, day). Returns rows written."""
        start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        stmt = (
            select(
                func.coalesce(SaleEvent.grade, "raw").label("bucket"),
                func.count(SaleEvent.id),
                func.avg(SaleEvent.price_usd),
                func.percentile_cont(0.5).within_group(SaleEvent.price_usd.asc()),
                func.min(SaleEvent.price_usd),
                func.max(SaleEvent.price_usd),
            )
            .where(
                SaleEvent.card_id == card_id,
                SaleEvent.sold_at >= start,
                SaleEvent.sold_at < end,
                SaleEvent.price_usd.is_not(None),
            )
            .group_by("bucket")
        )
        rows = (await self._session.execute(stmt)).all()
        written = 0
        for bucket, count, mean, median, mn, mx in rows:
            dialect = self._session.bind.dialect.name if self._session.bind else "postgresql"
            values = {
                "card_id": card_id,
                "day": start,
                "grade_bucket": str(bucket),
                "sample_count": int(count),
                "mean_usd": Decimal(mean or 0),
                "median_usd": Decimal(median or mean or 0),
                "min_usd": Decimal(mn or 0),
                "max_usd": Decimal(mx or 0),
            }
            if dialect == "postgresql":
                insert_stmt = pg_insert(CardPriceDaily).values(values)
                upsert_stmt = insert_stmt.on_conflict_do_update(
                    index_elements=["card_id", "day", "grade_bucket"],
                    set_={
                        "sample_count": insert_stmt.excluded.sample_count,
                        "mean_usd": insert_stmt.excluded.mean_usd,
                        "median_usd": insert_stmt.excluded.median_usd,
                        "min_usd": insert_stmt.excluded.min_usd,
                        "max_usd": insert_stmt.excluded.max_usd,
                    },
                )
                await self._session.execute(upsert_stmt)
            else:
                self._session.add(CardPriceDaily(**values))
            written += 1
        await self._session.commit()
        return written
