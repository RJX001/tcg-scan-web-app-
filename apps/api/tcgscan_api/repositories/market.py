from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from tcgscan_api.db.models import (
    CardIdentity,
    CardPopulation,
    CardPriceDaily,
    Game,
    SaleEvent,
    SaleKind,
)


@dataclass
class MoverRow:
    card: CardIdentity
    sales_count: int
    avg_usd: float | None
    prev_avg_usd: float | None
    change_pct: float | None
    last_sold_usd: float | None
    last_sold_at: datetime | None
    last_sold_grade: str | None
    pop_count: int | None = None


@dataclass
class RollupRow:
    card_id: uuid.UUID
    day: datetime
    median_usd: float


@dataclass
class ShopListingRow:
    card: CardIdentity
    source: str
    price: float
    currency: str
    price_usd: float | None
    grade: str | None
    listing_url: str | None
    listed_at: datetime


@dataclass
class SaleBrowseRow:
    card: CardIdentity
    source: str
    price: float
    currency: str
    price_usd: float | None
    grade: str | None
    listing_url: str | None
    sold_at: datetime


_RAW_GRADES = ("raw", "none", "")


def _grade_clause(grade: str):  # type: ignore[no-untyped-def]
    """Filter sale events by grade: 'raw', 'graded', or a company prefix (PSA, BGS, …)."""
    lowered = func.lower(func.coalesce(SaleEvent.grade, "raw"))
    if grade == "raw":
        return lowered.in_(_RAW_GRADES)
    if grade == "graded":
        return lowered.notin_(_RAW_GRADES)
    return SaleEvent.grade.ilike(f"{grade}%")


class MarketRepo:
    """Market-wide aggregations across card_identity + sale_event (the 'ladder')."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def movers(
        self,
        *,
        days: int = 30,
        game: str | None = None,
        q: str | None = None,
        grade: str | None = None,
        sort: str = "change",
        limit: int = 20,
        offset: int = 0,
    ) -> list[MoverRow]:
        now = datetime.now()
        cur_since = now - timedelta(days=days)
        prev_since = now - timedelta(days=days * 2)

        usd = case(
            (SaleEvent.price_usd.is_not(None), SaleEvent.price_usd),
            (SaleEvent.currency == "USD", SaleEvent.price),
        )
        cur_avg = func.avg(case((SaleEvent.sold_at >= cur_since, usd)))
        prev_avg = func.avg(
            case(
                (
                    and_(SaleEvent.sold_at >= prev_since, SaleEvent.sold_at < cur_since),
                    usd,
                )
            )
        )
        sales_count = func.count(case((SaleEvent.sold_at >= cur_since, 1)))
        change = case(
            (and_(cur_avg.is_not(None), prev_avg > 0), (cur_avg - prev_avg) / prev_avg * 100)
        )

        stmt = (
            select(
                CardIdentity,
                sales_count.label("sales_count"),
                cur_avg.label("avg_usd"),
                prev_avg.label("prev_avg_usd"),
                change.label("change_pct"),
            )
            .join(SaleEvent, SaleEvent.card_id == CardIdentity.id)
            .where(SaleEvent.kind == SaleKind.sold, SaleEvent.sold_at >= prev_since)
            .group_by(CardIdentity.id)
        )

        if game:
            try:
                stmt = stmt.where(CardIdentity.game == Game(game))
            except ValueError:
                return []
        if q and q.strip():
            pattern = f"%{q.strip()}%"
            stmt = stmt.where(
                or_(
                    CardIdentity.name.ilike(pattern),
                    CardIdentity.set_name.ilike(pattern),
                    CardIdentity.set_code.ilike(pattern),
                    CardIdentity.number.ilike(pattern),
                )
            )
        if grade:
            stmt = stmt.where(_grade_clause(grade))

        pop_sq = (
            select(
                CardPopulation.card_id.label("pop_card_id"),
                func.sum(CardPopulation.pop_count).label("pop_total"),
            )
            .group_by(CardPopulation.card_id)
            .subquery()
        )

        if sort == "change_asc":
            stmt = stmt.order_by(change.asc().nullslast(), CardIdentity.name)
        elif sort == "price":
            stmt = stmt.order_by(cur_avg.desc().nullslast(), CardIdentity.name)
        elif sort == "volume":
            stmt = stmt.order_by(sales_count.desc(), CardIdentity.name)
        elif sort == "recent":
            stmt = stmt.order_by(func.max(SaleEvent.sold_at).desc(), CardIdentity.name)
        elif sort == "pop":
            # max() because pop_total comes from a joined subquery outside the GROUP BY
            stmt = stmt.outerjoin(pop_sq, pop_sq.c.pop_card_id == CardIdentity.id).order_by(
                func.max(pop_sq.c.pop_total).desc().nullslast(), CardIdentity.name
            )
        elif sort == "market_cap":
            # avg price x graded population — proxy for total market value
            stmt = stmt.outerjoin(pop_sq, pop_sq.c.pop_card_id == CardIdentity.id).order_by(
                (cur_avg * func.coalesce(func.max(pop_sq.c.pop_total), 0)).desc().nullslast(),
                CardIdentity.name,
            )
        else:  # "change" (default): biggest gainers first
            stmt = stmt.order_by(change.desc().nullslast(), CardIdentity.name)

        stmt = stmt.limit(limit).offset(offset)
        rows = (await self._session.execute(stmt)).all()
        if not rows:
            return []

        card_ids = [r[0].id for r in rows]
        last_sales = await self._last_sales(card_ids, grade=grade)
        pops = await PopulationRepo(self._session).totals_for_cards(card_ids)
        out: list[MoverRow] = []
        for card, count, avg_usd, prev_avg_usd, change_pct in rows:
            last = last_sales.get(card.id)
            out.append(
                MoverRow(
                    card=card,
                    sales_count=int(count),
                    avg_usd=float(avg_usd) if avg_usd is not None else None,
                    prev_avg_usd=float(prev_avg_usd) if prev_avg_usd is not None else None,
                    change_pct=float(change_pct) if change_pct is not None else None,
                    last_sold_usd=last[0] if last else None,
                    last_sold_at=last[1] if last else None,
                    last_sold_grade=last[2] if last else None,
                    pop_count=pops.get(card.id),
                )
            )
        return out

    async def browse_listings(
        self,
        *,
        game: str | None = None,
        q: str | None = None,
        source: str | None = None,
        grade: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        listed_after: datetime | None = None,
        listed_before: datetime | None = None,
        sort: str = "recent",
        limit: int = 24,
        offset: int = 0,
    ) -> list[ShopListingRow]:
        """Cross-catalog active-listings browse (the 'shop')."""
        usd = case(
            (SaleEvent.price_usd.is_not(None), SaleEvent.price_usd),
            (SaleEvent.currency == "USD", SaleEvent.price),
        )
        stmt = (
            select(SaleEvent, CardIdentity)
            .join(CardIdentity, CardIdentity.id == SaleEvent.card_id)
            .where(SaleEvent.kind == SaleKind.listing)
        )

        if game:
            try:
                stmt = stmt.where(CardIdentity.game == Game(game))
            except ValueError:
                return []
        if q and q.strip():
            pattern = f"%{q.strip()}%"
            stmt = stmt.where(
                or_(
                    CardIdentity.name.ilike(pattern),
                    CardIdentity.set_name.ilike(pattern),
                    CardIdentity.set_code.ilike(pattern),
                    CardIdentity.number.ilike(pattern),
                )
            )
        if source:
            stmt = stmt.where(SaleEvent.source == source)
        if grade:
            stmt = stmt.where(
                _grade_clause(grade.lower() if grade.lower() in ("raw", "graded") else grade)
            )
        if min_price is not None:
            stmt = stmt.where(usd >= min_price)
        if max_price is not None:
            stmt = stmt.where(usd <= max_price)
        if listed_after is not None:
            stmt = stmt.where(SaleEvent.sold_at >= listed_after)
        if listed_before is not None:
            stmt = stmt.where(SaleEvent.sold_at <= listed_before)

        if sort == "price_asc":
            stmt = stmt.order_by(usd.asc().nullslast(), SaleEvent.sold_at.desc())
        elif sort == "price_desc":
            stmt = stmt.order_by(usd.desc().nullslast(), SaleEvent.sold_at.desc())
        else:  # "recent"
            stmt = stmt.order_by(SaleEvent.sold_at.desc())

        stmt = stmt.limit(limit).offset(offset)
        rows = (await self._session.execute(stmt)).all()
        return [
            ShopListingRow(
                card=card,
                source=ev.source,
                price=float(ev.price),
                currency=ev.currency,
                price_usd=float(ev.price_usd) if ev.price_usd is not None else None,
                grade=ev.grade,
                listing_url=ev.listing_url,
                listed_at=ev.sold_at,
            )
            for ev, card in rows
        ]

    async def browse_sales(
        self,
        *,
        game: str | None = None,
        q: str | None = None,
        source: str | None = None,
        grade: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        sold_after: datetime | None = None,
        sold_before: datetime | None = None,
        sort: str = "recent",
        limit: int = 24,
        offset: int = 0,
    ) -> list[SaleBrowseRow]:
        """Cross-catalog sold-comps browse (Card Ladder 'Sales' PRO parity)."""
        usd = case(
            (SaleEvent.price_usd.is_not(None), SaleEvent.price_usd),
            (SaleEvent.currency == "USD", SaleEvent.price),
        )
        stmt = (
            select(SaleEvent, CardIdentity)
            .join(CardIdentity, CardIdentity.id == SaleEvent.card_id)
            .where(SaleEvent.kind == SaleKind.sold)
        )

        if game:
            try:
                stmt = stmt.where(CardIdentity.game == Game(game))
            except ValueError:
                return []
        if q and q.strip():
            pattern = f"%{q.strip()}%"
            stmt = stmt.where(
                or_(
                    CardIdentity.name.ilike(pattern),
                    CardIdentity.set_name.ilike(pattern),
                    CardIdentity.set_code.ilike(pattern),
                    CardIdentity.number.ilike(pattern),
                )
            )
        if source:
            stmt = stmt.where(SaleEvent.source == source)
        if grade:
            stmt = stmt.where(
                _grade_clause(grade.lower() if grade.lower() in ("raw", "graded") else grade)
            )
        if min_price is not None:
            stmt = stmt.where(usd >= min_price)
        if max_price is not None:
            stmt = stmt.where(usd <= max_price)
        if sold_after is not None:
            stmt = stmt.where(SaleEvent.sold_at >= sold_after)
        if sold_before is not None:
            stmt = stmt.where(SaleEvent.sold_at <= sold_before)

        if sort == "price_asc":
            stmt = stmt.order_by(usd.asc().nullslast(), SaleEvent.sold_at.desc())
        elif sort == "price_desc":
            stmt = stmt.order_by(usd.desc().nullslast(), SaleEvent.sold_at.desc())
        else:
            stmt = stmt.order_by(SaleEvent.sold_at.desc())

        stmt = stmt.limit(limit).offset(offset)
        rows = (await self._session.execute(stmt)).all()
        return [
            SaleBrowseRow(
                card=card,
                source=ev.source,
                price=float(ev.price),
                currency=ev.currency,
                price_usd=float(ev.price_usd) if ev.price_usd is not None else None,
                grade=ev.grade,
                listing_url=ev.listing_url,
                sold_at=ev.sold_at,
            )
            for ev, card in rows
        ]

    async def daily_rollups(
        self,
        *,
        days: int = 90,
        game: str | None = None,
        grade_bucket: str = "raw",
    ) -> list[RollupRow]:
        """Per-card daily medians used to compute composite market indexes."""
        since = datetime.now() - timedelta(days=days)
        stmt = (
            select(CardPriceDaily.card_id, CardPriceDaily.day, CardPriceDaily.median_usd)
            .where(CardPriceDaily.grade_bucket == grade_bucket, CardPriceDaily.day >= since)
            .order_by(CardPriceDaily.day.asc())
        )
        if game:
            try:
                stmt = stmt.join(CardIdentity, CardIdentity.id == CardPriceDaily.card_id).where(
                    CardIdentity.game == Game(game)
                )
            except ValueError:
                return []
        rows = (await self._session.execute(stmt)).all()
        return [
            RollupRow(card_id=card_id, day=day, median_usd=float(median))
            for card_id, day, median in rows
        ]

    async def _last_sales(
        self, card_ids: list[uuid.UUID], *, grade: str | None = None
    ) -> dict[uuid.UUID, tuple[float | None, datetime, str | None]]:
        """Most recent sold event per card: (price_usd, sold_at, grade)."""
        rn = (
            func.row_number()
            .over(partition_by=SaleEvent.card_id, order_by=SaleEvent.sold_at.desc())
            .label("rn")
        )
        inner = select(
            SaleEvent.card_id,
            SaleEvent.price_usd,
            SaleEvent.price,
            SaleEvent.currency,
            SaleEvent.grade,
            SaleEvent.sold_at,
            rn,
        ).where(SaleEvent.card_id.in_(card_ids), SaleEvent.kind == SaleKind.sold)
        if grade:
            inner = inner.where(_grade_clause(grade))
        sub = inner.subquery()
        stmt = select(
            sub.c.card_id, sub.c.price_usd, sub.c.price, sub.c.currency, sub.c.grade, sub.c.sold_at
        ).where(sub.c.rn == 1)
        rows = (await self._session.execute(stmt)).all()
        out: dict[uuid.UUID, tuple[float | None, datetime, str | None]] = {}
        for card_id, price_usd, price, currency, grade, sold_at in rows:
            if price_usd is not None:
                usd: float | None = float(price_usd)
            elif currency == "USD":
                usd = float(price)
            else:
                usd = None
            key = card_id if isinstance(card_id, uuid.UUID) else uuid.UUID(str(card_id))
            out[key] = (usd, sold_at, grade)
        return out


class PopulationRepo:
    """Grading population snapshots (PSA/BGS/CGC) per card + grade."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_many(self, rows: list[dict[str, object]]) -> int:
        if not rows:
            return 0
        dialect = self._session.bind.dialect.name if self._session.bind else "postgresql"
        if dialect == "postgresql":
            stmt = pg_insert(CardPopulation).values(rows)
            stmt = stmt.on_conflict_do_update(
                index_elements=["card_id", "grade_company", "grade"],
                set_={"pop_count": stmt.excluded.pop_count, "as_of": stmt.excluded.as_of},
            )
            await self._session.execute(stmt)
        else:
            for r in rows:
                existing = await self._session.get(
                    CardPopulation, (r["card_id"], r["grade_company"], r["grade"])
                )
                if existing is None:
                    self._session.add(CardPopulation(**r))
                else:
                    pop = r["pop_count"]
                    existing.pop_count = pop if isinstance(pop, int) else int(str(pop))
                    as_of = r.get("as_of")
                    if isinstance(as_of, datetime):
                        existing.as_of = as_of
        await self._session.commit()
        return len(rows)

    async def for_card(self, card_id: uuid.UUID) -> list[CardPopulation]:
        stmt = (
            select(CardPopulation)
            .where(CardPopulation.card_id == card_id)
            .order_by(CardPopulation.grade_company, CardPopulation.grade.desc())
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def totals_for_cards(self, card_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
        if not card_ids:
            return {}
        stmt = (
            select(CardPopulation.card_id, func.sum(CardPopulation.pop_count))
            .where(CardPopulation.card_id.in_(card_ids))
            .group_by(CardPopulation.card_id)
        )
        rows = (await self._session.execute(stmt)).all()
        out: dict[uuid.UUID, int] = {}
        for card_id, total in rows:
            key = card_id if isinstance(card_id, uuid.UUID) else uuid.UUID(str(card_id))
            out[key] = int(total)
        return out
