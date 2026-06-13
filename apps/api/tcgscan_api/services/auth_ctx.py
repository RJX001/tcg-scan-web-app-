"""Resolve authenticated user with DB-backed tier."""

from __future__ import annotations


from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from tcgscan_api.db.models import User, UserTier
from tcgscan_api.middleware.auth import AuthUser
from tcgscan_api.repositories.users import UsersRepo


async def resolve_db_user(session: AsyncSession, request: Request) -> AuthUser:
    """Load or create user row; attach real id + tier from Postgres."""
    principal = getattr(request.state, "user", None)
    if principal is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    user = await UsersRepo(session).get_or_create(
        clerk_id=principal.clerk_id, email=principal.email
    )
    return AuthUser(
        id=user.id,
        clerk_id=user.clerk_id,
        tier=_tier_value(user),
        email=user.email,
    )


def _tier_value(user: User) -> str:
    tier = user.tier
    return tier.value if isinstance(tier, UserTier) else str(tier)


async def optional_db_user(session: AsyncSession, request: Request) -> AuthUser | None:
    principal = getattr(request.state, "user", None)
    if principal is None:
        return None
    user = await UsersRepo(session).get_or_create(
        clerk_id=principal.clerk_id, email=principal.email
    )
    return AuthUser(
        id=user.id,
        clerk_id=user.clerk_id,
        tier=_tier_value(user),
        email=user.email,
    )


def is_pro(user: AuthUser) -> bool:
    return user.tier == UserTier.pro.value or user.tier == "pro"
