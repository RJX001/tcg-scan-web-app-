from __future__ import annotations

import uuid

import structlog
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

log = structlog.get_logger()

# Canonical production owner after Clerk → Supabase migration. Prefer this row
# (owner/admin + billing) when repairing a conflicting supabase_user_id link.
CANONICAL_OWNER_EMAIL = "rajanpatel2001@hotmail.com"

_ROLE_RANK = {
    UserRole.owner: 4,
    UserRole.admin_senior: 3,
    UserRole.admin: 2,
    UserRole.user: 1,
}


def _role_value(role: UserRole | str | None) -> str:
    if role is None:
        return UserRole.user.value
    return role.value if isinstance(role, UserRole) else str(role)


def _role_rank(user: User) -> int:
    return _ROLE_RANK.get(UserRole(_role_value(user.role)), 0)


def _has_billing_data(user: User) -> bool:
    return bool(user.stripe_customer_id)


def select_canonical_user(matches: list[User]) -> User:
    """Pick the migrated owner/admin (or billed) row among email duplicates."""
    return max(
        matches,
        key=lambda u: (
            _role_rank(u),
            1 if _has_billing_data(u) else 0,
            1 if u.account_number else 0,
            # Prefer older rows when ranks tie (original migrated account).
            -(u.created_at.timestamp() if u.created_at else 0.0),
        ),
    )


class UsersRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _next_account_seq(self) -> int:
        bind = self._session.get_bind()
        if bind is not None and bind.dialect.name == "postgresql":
            try:
                result = await self._session.execute(text("SELECT nextval('user_account_seq')"))
                return int(result.scalar_one())
            except Exception:
                log.warning("users.account_seq_missing", fallback="max_plus_one")
        row = await self._session.execute(
            text("SELECT COALESCE(MAX(account_seq), 9) + 1 FROM users")
        )
        return int(row.scalar_one())

    async def _users_by_email(self, email: str) -> list[User]:
        stmt = (
            select(User)
            .where(func.lower(User.email) == email.lower())
            .order_by(User.created_at.asc())
        )
        return list((await self._session.execute(stmt)).scalars().all())

    def _is_owner_migration_email(self, email: str) -> bool:
        lowered = email.lower()
        if lowered == CANONICAL_OWNER_EMAIL.lower():
            return True
        settings = get_settings()
        return bool(settings.owner_email and lowered == settings.owner_email.lower())

    async def _linkable_user_by_email(self, email: str, supabase_user_id: str) -> User | None:
        matches = await self._users_by_email(email)
        if not matches:
            return None
        if len(matches) > 1:
            log.warning("users.duplicate_email", email=email, count=len(matches))
        for user in matches:
            if user.supabase_user_id == supabase_user_id:
                return user

        # Migrated owner/admin: always prefer the canonical row (role/billing),
        # even when a blank duplicate has a null SID or the owner has a stale SID.
        if self._is_owner_migration_email(email):
            canonical = select_canonical_user(matches)
            log.info(
                "users.relink_owner_supabase_id",
                email=email,
                user_id=str(canonical.id),
                previous_supabase_user_id=canonical.supabase_user_id,
                supabase_user_id=supabase_user_id,
                role=_role_value(canonical.role),
            )
            return canonical

        linkable = [user for user in matches if user.supabase_user_id is None]
        if linkable:
            if len(linkable) > 1:
                log.warning(
                    "users.multiple_linkable_email_rows", email=email, count=len(linkable)
                )
            return select_canonical_user(linkable)

        raise ValueError(
            "Account email is linked to another sign-in identity. Contact support."
        )

    async def _attach_supabase_id(self, user: User, supabase_user_id: str) -> User:
        """Point ``user`` at ``supabase_user_id``, freeing any other row that held it."""
        if user.supabase_user_id == supabase_user_id:
            return user

        stmt = select(User).where(User.supabase_user_id == supabase_user_id)
        holder = (await self._session.execute(stmt)).scalar_one_or_none()
        if holder is not None and holder.id != user.id:
            # Empty duplicate created before the owner row was found — free the SID
            # without deleting Stripe/account data on the canonical row.
            if _role_rank(holder) <= _ROLE_RANK[UserRole.user] and not _has_billing_data(holder):
                log.info(
                    "users.clear_duplicate_supabase_id",
                    duplicate_user_id=str(holder.id),
                    supabase_user_id=supabase_user_id,
                    canonical_user_id=str(user.id),
                )
                holder.supabase_user_id = None
                # Flush clear first so the unique index never sees two SIDs at once.
                await self._session.flush()
            else:
                raise ValueError(
                    "Account email is linked to another sign-in identity. Contact support."
                )

        user.supabase_user_id = supabase_user_id
        await self._session.commit()
        await self._session.refresh(user)
        return user

    async def _maybe_promote_owner(self, user: User) -> User:
        settings = get_settings()
        owner_emails = {CANONICAL_OWNER_EMAIL.lower()}
        if settings.owner_email:
            owner_emails.add(settings.owner_email.lower())
        if (
            user.email
            and user.email.lower() in owner_emails
            and user.role != UserRole.owner
        ):
            user.role = UserRole.owner
            await self._session.commit()
            await self._session.refresh(user)
        return user

    async def get_or_create(self, *, supabase_user_id: str, email: str | None = None) -> User:
        stmt = select(User).where(User.supabase_user_id == supabase_user_id)
        existing = (await self._session.execute(stmt)).scalar_one_or_none()
        if existing:
            # If this SID landed on a blank free row but the email belongs to the
            # migrated owner/admin account, reclaim the SID onto that canonical row.
            if email and self._is_owner_migration_email(email):
                matches = await self._users_by_email(email)
                if matches:
                    canonical = select_canonical_user(matches)
                    if canonical.id != existing.id and (
                        _role_rank(canonical) > _role_rank(existing)
                        or _has_billing_data(canonical)
                    ):
                        attached = await self._attach_supabase_id(canonical, supabase_user_id)
                        if not attached.email:
                            attached.email = email
                            await self._session.commit()
                            await self._session.refresh(attached)
                        return await self._maybe_promote_owner(attached)

            changed = False
            if email and not existing.email:
                existing.email = email
                changed = True
            if changed:
                await self._session.commit()
                await self._session.refresh(existing)
            return await self._maybe_promote_owner(existing)

        if email:
            linked = await self._linkable_user_by_email(email, supabase_user_id)
            if linked is not None:
                attached = await self._attach_supabase_id(linked, supabase_user_id)
                if not attached.email:
                    attached.email = email
                    await self._session.commit()
                    await self._session.refresh(attached)
                return await self._maybe_promote_owner(attached)

        seq = await self._next_account_seq()
        user = User(
            supabase_user_id=supabase_user_id,
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
