"""Marketplace listings persistence."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.exc import DBAPIError, ProgrammingError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from tcgscan_api.db.models import MarketplaceListing


@dataclass
class MarketplaceListingRow:
    listing: MarketplaceListing


class MarketplaceListingsRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_batch(self, rows: list[dict[str, object]]) -> tuple[int, int, int]:
        inserted = 0
        updated = 0
        skipped = 0

        for row in rows:
            source = row.get("source")
            source_listing_id = row.get("source_listing_id")
            if not source or not source_listing_id:
                skipped += 1
                continue
            existing = (
                await self._session.execute(
                    select(MarketplaceListing).where(
                        MarketplaceListing.source == source,
                        MarketplaceListing.source_listing_id == str(source_listing_id),
                    )
                )
            ).scalar_one_or_none()

            values = {
                "id": uuid.uuid4(),
                "source": str(source),
                "source_listing_id": str(source_listing_id),
                "title": row["title"],
                "price": row["price"],
                "currency": row.get("currency", "USD"),
                "condition": row.get("condition"),
                "image_url": row.get("image_url"),
                "item_url": row["item_url"],
                "seller_username": row.get("seller_username"),
                "marketplace": row.get("marketplace", "EBAY_GB"),
                "listing_status": row.get("listing_status", "active"),
                "affiliate_status": row.get("affiliate_status"),
                "grade": row.get("grade"),
                "raw_metadata": row.get("raw_metadata"),
                "observed_at": row.get("observed_at", datetime.now()),
            }
            if existing is None:
                self._session.add(MarketplaceListing(**values))
                inserted += 1
            else:
                for key, val in values.items():
                    if key == "id":
                        continue
                    setattr(existing, key, val)
                updated += 1

        await self._session.commit()
        return inserted, updated, skipped

    async def count_active(self, *, source: str | None = None) -> int:
        stmt = (
            select(func.count())
            .select_from(MarketplaceListing)
            .where(MarketplaceListing.listing_status == "active")
        )
        if source:
            stmt = stmt.where(MarketplaceListing.source == source)
        try:
            return int((await self._session.execute(stmt)).scalar_one())
        except (ProgrammingError, DBAPIError, SQLAlchemyError):
            await self._session.rollback()
            return 0

    async def browse(
        self,
        *,
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
    ) -> list[MarketplaceListing]:
        stmt = select(MarketplaceListing).where(MarketplaceListing.listing_status == "active")
        if source:
            stmt = stmt.where(MarketplaceListing.source == source)
        if q and q.strip():
            pattern = f"%{q.strip()}%"
            stmt = stmt.where(
                or_(
                    MarketplaceListing.title.ilike(pattern),
                    MarketplaceListing.seller_username.ilike(pattern),
                )
            )
        if grade:
            g = grade.lower()
            if g == "raw":
                stmt = stmt.where(
                    or_(MarketplaceListing.grade.is_(None), MarketplaceListing.grade == "raw")
                )
            elif g == "graded":
                stmt = stmt.where(
                    MarketplaceListing.grade.is_not(None), MarketplaceListing.grade != "raw"
                )
            else:
                stmt = stmt.where(MarketplaceListing.grade.ilike(f"{grade}%"))
        if min_price is not None:
            stmt = stmt.where(MarketplaceListing.price >= min_price)
        if max_price is not None:
            stmt = stmt.where(MarketplaceListing.price <= max_price)
        if listed_after is not None:
            stmt = stmt.where(MarketplaceListing.observed_at >= listed_after)
        if listed_before is not None:
            stmt = stmt.where(MarketplaceListing.observed_at <= listed_before)

        if sort == "price_asc":
            stmt = stmt.order_by(
                MarketplaceListing.price.asc(), MarketplaceListing.observed_at.desc()
            )
        elif sort == "price_desc":
            stmt = stmt.order_by(
                MarketplaceListing.price.desc(), MarketplaceListing.observed_at.desc()
            )
        else:
            stmt = stmt.order_by(MarketplaceListing.observed_at.desc())

        stmt = stmt.limit(limit).offset(offset)
        return list((await self._session.execute(stmt)).scalars().all())
