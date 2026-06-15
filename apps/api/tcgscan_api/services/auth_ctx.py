"""Resolve authenticated user with DB-backed tier."""

from __future__ import annotations


from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from tcgscan_api.db.models import User, UserRole, UserTier
from tcgscan_api.middleware.auth import AuthUser
from tcgscan_api.repositories.users import UsersRepo


async def resolve_db_user(session: AsyncSession, request: Request) -> AuthUser:
    """Load or create user row; attach real id + tier from Postgres."""
    principal = getattr(request.state, "user", None)
    if principal is None or not principal.supabase_user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    user = await UsersRepo(session).get_or_create(
        supabase_user_id=principal.supabase_user_id, email=principal.email
    )
    return AuthUser(
        id=user.id,
        supabase_user_id=user.supabase_user_id or principal.supabase_user_id,
        tier=_tier_value(user),
        role=_role_value(user),
        email=user.email,
    )


def _tier_value(user: User) -> str:
    tier = user.tier
    return tier.value if isinstance(tier, UserTier) else str(tier)


def _role_value(user: User) -> str:
    role = user.role
    return role.value if isinstance(role, UserRole) else str(role)


async def optional_db_user(session: AsyncSession, request: Request) -> AuthUser | None:
    principal = getattr(request.state, "user", None)
    if principal is None or not principal.supabase_user_id:
        return None
    user = await UsersRepo(session).get_or_create(
        supabase_user_id=principal.supabase_user_id, email=principal.email
    )
    return AuthUser(
        id=user.id,
        supabase_user_id=user.supabase_user_id or principal.supabase_user_id,
        tier=_tier_value(user),
        role=_role_value(user),
        email=user.email,
    )


def is_pro(user: AuthUser) -> bool:
    return user.tier == UserTier.pro.value or user.tier == "pro"
