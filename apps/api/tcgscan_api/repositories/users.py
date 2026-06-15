from __future__ import annotations

import uuid

from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from tcgscan_api.config import get_settings
from tcgscan_api.db.models import (
    PortfolioItem,
    PriceAlert,
    SavedSearch,
    User,
    UserRole,
    UserTier,
    WatchlistItem,
)


class UsersRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _next_account_seq(self) -> int:
        bind = self._session.get_bind()
        if bind is not None and bind.dialect.name == "postgresql":
            result = await self._session.execute(text("SELECT nextval('user_account_seq')"))
            return int(result.scalar_one())
        row = await self._session.execute(
            text("SELECT COALESCE(MAX(account_seq), 9) + 1 FROM users")
        )
        return int(row.scalar_one())

    async def _maybe_promote_owner(self, user: User) -> User:
        settings = get_settings()
        if (
            settings.owner_email
            and user.email
            and user.email.lower() == settings.owner_email.lower()
            and user.role != UserRole.owner
        ):
            user.role = UserRole.owner
            await self._session.commit()
            await self._session.refresh(user)
        return user

    async def get_or_create(self, *, clerk_id: str, email: str | None = None) -> User:
        stmt = select(User).where(User.clerk_id == clerk_id)
        existing = (await self._session.execute(stmt)).scalar_one_or_none()
        if existing:
            changed = False
            if email and not existing.email:
                existing.email = email
                changed = True
            if changed:
                await self._session.commit()
                await self._session.refresh(existing)
            return await self._maybe_promote_owner(existing)

        seq = await self._next_account_seq()
        user = User(
            clerk_id=clerk_id,
            email=email,
            tier=UserTier.free,
            role=UserRole.user,
            account_seq=seq,
            account_number=f"{seq:06d}",
        )
        self._session.add(user)
        await self._session.commit()
        await self._session.refresh(user)
        return await self._maybe_promote_owner(user)

    async def get_or_create_by_supabase(
        self, *, supabase_user_id: str, email: str | None = None
    ) -> User:
        stmt = select(User).where(User.supabase_user_id == supabase_user_id)
        existing = (await self._session.execute(stmt)).scalar_one_or_none()
        if existing:
            changed = False
            if email and not existing.email:
                existing.email = email
                changed = True
            if changed:
                await self._session.commit()
                await self._session.refresh(existing)
            return await self._maybe_promote_owner(existing)

        if email:
            email_stmt = select(User).where(func.lower(User.email) == email.lower())
            linked = (await self._session.execute(email_stmt)).scalar_one_or_none()
            if linked is not None and linked.supabase_user_id is None:
                linked.supabase_user_id = supabase_user_id
                if not linked.email:
                    linked.email = email
                await self._session.commit()
                await self._session.refresh(linked)
                return await self._maybe_promote_owner(linked)

        seq = await self._next_account_seq()
        user = User(
            supabase_user_id=supabase_user_id,
            clerk_id=None,
            email=email,
            tier=UserTier.free,
            role=UserRole.user,
            account_seq=seq,
            account_number=f"{seq:06d}",
        )
        self._session.add(user)
        await self._session.commit()
        await self._session.refresh(user)
        return await self._maybe_promote_owner(user)

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self._session.get(User, user_id)

    async def get_by_stripe_customer(self, customer_id: str) -> User | None:
        stmt = select(User).where(User.stripe_customer_id == customer_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def set_stripe_customer(self, user_id: uuid.UUID, customer_id: str) -> None:
        user = await self._session.get(User, user_id)
        if user is None:
            return
        user.stripe_customer_id = customer_id
        await self._session.commit()

    async def set_tier(self, user_id: uuid.UUID, tier: UserTier) -> None:
        await self._session.execute(update(User).where(User.id == user_id).values(tier=tier))
        await self._session.commit()

    async def set_role(self, user_id: uuid.UUID, role: UserRole) -> User | None:
        user = await self._session.get(User, user_id)
        if user is None:
            return None
        user.role = role
        await self._session.commit()
        await self._session.refresh(user)
        return user

    async def set_account_number(self, user_id: uuid.UUID, account_number: str) -> User | None:
        user = await self._session.get(User, user_id)
        if user is None:
            return None
        user.account_number = account_number
        await self._session.commit()
        await self._session.refresh(user)
        return user

    async def account_number_taken(self, account_number: str, *, exclude_id: uuid.UUID) -> bool:
        stmt = select(User.id).where(User.account_number == account_number, User.id != exclude_id)
        return (await self._session.execute(stmt)).scalar_one_or_none() is not None

    async def set_comps_days(self, user_id: uuid.UUID, days: int) -> User | None:
        user = await self._session.get(User, user_id)
        if user is None:
            return None
        user.comps_days = days
        await self._session.commit()
        await self._session.refresh(user)
        return user

    async def count_portfolio_items(self, user_id: uuid.UUID) -> int:
        stmt = (
            select(func.count()).select_from(PortfolioItem).where(PortfolioItem.user_id == user_id)
        )
        return int((await self._session.execute(stmt)).scalar_one())


class PortfolioRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_user(self, user_id: uuid.UUID) -> list[PortfolioItem]:
        stmt = select(PortfolioItem).where(PortfolioItem.user_id == user_id)
        return list((await self._session.execute(stmt)).scalars().all())

    async def add(
        self,
        *,
        user_id: uuid.UUID,
        card_id: uuid.UUID,
        quantity: int = 1,
        cost_basis_usd: float | None = None,
        notes: str | None = None,
    ) -> PortfolioItem:
        stmt = select(PortfolioItem).where(
            PortfolioItem.user_id == user_id, PortfolioItem.card_id == card_id
        )
        existing = (await self._session.execute(stmt)).scalar_one_or_none()
        if existing:
            existing.quantity += quantity
            if cost_basis_usd is not None:
                from decimal import Decimal

                existing.cost_basis_usd = Decimal(str(cost_basis_usd))
            if notes:
                existing.notes = notes
            await self._session.commit()
            await self._session.refresh(existing)
            return existing
        from decimal import Decimal

        item = PortfolioItem(
            user_id=user_id,
            card_id=card_id,
            quantity=quantity,
            cost_basis_usd=Decimal(str(cost_basis_usd)) if cost_basis_usd is not None else None,
            notes=notes,
        )
        self._session.add(item)
        await self._session.commit()
        await self._session.refresh(item)
        return item

    async def remove(self, user_id: uuid.UUID, item_id: uuid.UUID) -> bool:
        item = await self._session.get(PortfolioItem, item_id)
        if item is None or item.user_id != user_id:
            return False
        await self._session.delete(item)
        await self._session.commit()
        return True


class AlertsRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_user(self, user_id: uuid.UUID) -> list[PriceAlert]:
        stmt = select(PriceAlert).where(PriceAlert.user_id == user_id)
        return list((await self._session.execute(stmt)).scalars().all())

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        card_id: uuid.UUID,
        direction: str,
        threshold_usd: float,
        grade_filter: str | None = None,
    ) -> PriceAlert:
        from decimal import Decimal

        from tcgscan_api.db.models import AlertDirection

        alert = PriceAlert(
            user_id=user_id,
            card_id=card_id,
            direction=AlertDirection(direction),
            threshold_usd=Decimal(str(threshold_usd)),
            grade_filter=grade_filter,
            active=True,
        )
        self._session.add(alert)
        await self._session.commit()
        await self._session.refresh(alert)
        return alert

    async def delete(self, user_id: uuid.UUID, alert_id: uuid.UUID) -> bool:
        alert = await self._session.get(PriceAlert, alert_id)
        if alert is None or alert.user_id != user_id:
            return False
        await self._session.delete(alert)
        await self._session.commit()
        return True

    async def list_active(self) -> list[PriceAlert]:
        stmt = select(PriceAlert).where(PriceAlert.active.is_(True))
        return list((await self._session.execute(stmt)).scalars().all())


class WatchlistRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_user(self, user_id: uuid.UUID) -> list[WatchlistItem]:
        stmt = (
            select(WatchlistItem)
            .where(WatchlistItem.user_id == user_id)
            .order_by(WatchlistItem.created_at.desc())
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def get_for_card(self, user_id: uuid.UUID, card_id: uuid.UUID) -> WatchlistItem | None:
        stmt = select(WatchlistItem).where(
            WatchlistItem.user_id == user_id, WatchlistItem.card_id == card_id
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def add(self, *, user_id: uuid.UUID, card_id: uuid.UUID) -> WatchlistItem:
        existing = await self.get_for_card(user_id, card_id)
        if existing:
            return existing
        item = WatchlistItem(user_id=user_id, card_id=card_id)
        self._session.add(item)
        await self._session.commit()
        await self._session.refresh(item)
        return item

    async def remove(self, user_id: uuid.UUID, item_id: uuid.UUID) -> bool:
        item = await self._session.get(WatchlistItem, item_id)
        if item is None or item.user_id != user_id:
            return False
        await self._session.delete(item)
        await self._session.commit()
        return True


class SavedSearchRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_user(self, user_id: uuid.UUID) -> list[SavedSearch]:
        stmt = (
            select(SavedSearch)
            .where(SavedSearch.user_id == user_id)
            .order_by(SavedSearch.created_at.desc())
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def upsert(
        self, *, user_id: uuid.UUID, name: str, params: dict[str, object]
    ) -> SavedSearch:
        stmt = select(SavedSearch).where(SavedSearch.user_id == user_id, SavedSearch.name == name)
        existing = (await self._session.execute(stmt)).scalar_one_or_none()
        if existing:
            existing.params = params
            await self._session.commit()
            await self._session.refresh(existing)
            return existing
        search = SavedSearch(user_id=user_id, name=name, params=params)
        self._session.add(search)
        await self._session.commit()
        await self._session.refresh(search)
        return search

    async def delete(self, user_id: uuid.UUID, search_id: uuid.UUID) -> bool:
        search = await self._session.get(SavedSearch, search_id)
        if search is None or search.user_id != user_id:
            return False
        await self._session.delete(search)
        await self._session.commit()
        return True
