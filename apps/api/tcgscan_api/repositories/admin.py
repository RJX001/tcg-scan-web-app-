"""Admin dashboard aggregations."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from tcgscan_api.db.models import (
    CardIdentity,
    CardPriceDaily,
    PortfolioItem,
    PriceAlert,
    SaleEvent,
    User,
    UserTier,
    WatchlistItem,
)


class AdminRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def overview(self) -> dict[str, int | str | None]:
        now = datetime.now(timezone.utc)
        day_ago = now - timedelta(hours=24)
        week_ago = now - timedelta(days=7)

        async def _count(stmt: Any) -> int:
            return int((await self._session.execute(stmt)).scalar_one())

        total_users = await _count(select(func.count()).select_from(User))
        pro_users = await _count(
            select(func.count()).select_from(User).where(User.tier == UserTier.pro)
        )
        free_users = total_users - pro_users
        new_users_24h = await _count(
            select(func.count()).select_from(User).where(User.created_at >= day_ago)
        )
        new_users_7d = await _count(
            select(func.count()).select_from(User).where(User.created_at >= week_ago)
        )
        total_portfolio_items = await _count(
            select(func.count()).select_from(PortfolioItem)
        )
        total_watchlist_items = await _count(
            select(func.count()).select_from(WatchlistItem)
        )
        total_alerts = await _count(select(func.count()).select_from(PriceAlert))
        cards_in_catalogue = await _count(select(func.count()).select_from(CardIdentity))
        sale_events_total = await _count(select(func.count()).select_from(SaleEvent))
        sale_events_24h = await _count(
            select(func.count())
            .select_from(SaleEvent)
            .where(SaleEvent.ingested_at >= day_ago)
        )
        last_rollup = (
            await self._session.execute(select(func.max(CardPriceDaily.day)))
        ).scalar_one()

        return {
            "total_users": total_users,
            "pro_users": pro_users,
            "free_users": free_users,
            "new_users_24h": new_users_24h,
            "new_users_7d": new_users_7d,
            "total_portfolio_items": total_portfolio_items,
            "total_watchlist_items": total_watchlist_items,
            "total_alerts": total_alerts,
            "cards_in_catalogue": cards_in_catalogue,
            "sale_events_total": sale_events_total,
            "sale_events_24h": sale_events_24h,
            "last_price_rollup": last_rollup.isoformat() if last_rollup else None,
        }

    async def list_users(
        self, *, limit: int = 50, offset: int = 0, q: str | None = None
    ) -> tuple[list[dict[str, object]], int]:
        base = select(User)
        if q:
            like = f"%{q.strip().lower()}%"
            base = base.where(
                func.lower(User.email).like(like)
                | User.account_number.like(like)
                | User.clerk_id.like(like)
            )
        count_stmt = select(func.count()).select_from(User)
        if q:
            like = f"%{q.strip().lower()}%"
            count_stmt = count_stmt.where(
                func.lower(User.email).like(like)
                | User.account_number.like(like)
                | User.clerk_id.like(like)
            )
        total = int((await self._session.execute(count_stmt)).scalar_one())
        stmt = base.order_by(User.created_at.desc()).limit(limit).offset(offset)
        users = list((await self._session.execute(stmt)).scalars().all())

        portfolio_counts: dict[uuid.UUID, int] = {}
        if users:
            ids = [u.id for u in users]
            rows = await self._session.execute(
                select(PortfolioItem.user_id, func.count())
                .where(PortfolioItem.user_id.in_(ids))
                .group_by(PortfolioItem.user_id)
            )
            portfolio_counts = {uid: int(cnt) for uid, cnt in rows.all()}

        items: list[dict[str, object]] = []
        for user in users:
            tier = user.tier.value if hasattr(user.tier, "value") else str(user.tier)
            role = user.role.value if hasattr(user.role, "value") else str(user.role)
            items.append(
                {
                    "id": str(user.id),
                    "account_number": user.account_number,
                    "email": user.email,
                    "tier": tier,
                    "role": role,
                    "created_at": user.created_at.isoformat(),
                    "portfolio_count": portfolio_counts.get(user.id, 0),
                    "last_seen": None,
                }
            )
        return items, total

    async def user_detail(self, user_id: uuid.UUID) -> dict[str, object] | None:
        user = await self._session.get(User, user_id)
        if user is None:
            return None

        async def _count_model(table: object, fk_col: object) -> int:
            stmt = select(func.count()).select_from(table).where(fk_col == user_id)  # type: ignore[arg-type]
            return int((await self._session.execute(stmt)).scalar_one())

        tier = user.tier.value if hasattr(user.tier, "value") else str(user.tier)
        role = user.role.value if hasattr(user.role, "value") else str(user.role)
        return {
            "id": str(user.id),
            "account_number": user.account_number,
            "email": user.email,
            "tier": tier,
            "role": role,
            "created_at": user.created_at.isoformat(),
            "stripe_customer_id": user.stripe_customer_id,
            "portfolio_count": await _count_model(PortfolioItem, PortfolioItem.user_id),
            "watchlist_count": await _count_model(WatchlistItem, WatchlistItem.user_id),
            "alert_count": await _count_model(PriceAlert, PriceAlert.user_id),
        }

    async def revenue(self) -> dict[str, float | int]:
        now = datetime.now(timezone.utc)
        month_ago = now - timedelta(days=30)
        pro_count = int(
            (
                await self._session.execute(
                    select(func.count()).select_from(User).where(User.tier == UserTier.pro)
                )
            ).scalar_one()
        )
        new_pro_30d = int(
            (
                await self._session.execute(
                    select(func.count())
                    .select_from(User)
                    .where(User.tier == UserTier.pro, User.created_at >= month_ago)
                )
            ).scalar_one()
        )
        mrr = round(pro_count * 9.99, 2)
        return {
            "mrr_usd": mrr,
            "active_pro_count": pro_count,
            "new_subs_30d": new_pro_30d,
            "churn_30d": 0,
        }

    async def data_health(self) -> list[dict[str, object]]:
        now = datetime.now(timezone.utc)
        sources = (
            await self._session.execute(
                select(SaleEvent.source).distinct().order_by(SaleEvent.source)
            )
        ).scalars().all()
        if not sources:
            sources = ["ebay", "tcgplayer", "cardmarket"]

        out: list[dict[str, object]] = []
        for source in sources:
            row_count = int(
                (
                    await self._session.execute(
                        select(func.count())
                        .select_from(SaleEvent)
                        .where(SaleEvent.source == source)
                    )
                ).scalar_one()
            )
            last_ingested = (
                await self._session.execute(
                    select(func.max(SaleEvent.ingested_at)).where(SaleEvent.source == source)
                )
            ).scalar_one()
            status = "down"
            if last_ingested is not None:
                age_h = (now - last_ingested).total_seconds() / 3600
                if age_h < 26:
                    status = "ok"
                elif age_h < 24 * 7:
                    status = "stale"
            out.append(
                {
                    "source": source,
                    "row_count": row_count,
                    "last_ingested_at": last_ingested.isoformat() if last_ingested else None,
                    "status": status,
                }
            )
        return out

    async def db_reachable(self) -> bool:
        try:
            await self._session.execute(text("SELECT 1"))
            return True
        except Exception:
            return False
