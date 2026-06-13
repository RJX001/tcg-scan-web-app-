"""Subscription tier enforcement."""

from __future__ import annotations

from fastapi import HTTPException

from tcgscan_api.config import get_settings
from tcgscan_api.middleware.auth import AuthUser
from tcgscan_api.services.auth_ctx import is_pro


def require_pro(user: AuthUser, *, feature: str = "This feature") -> None:
    if not is_pro(user):
        raise HTTPException(
            status_code=403,
            detail=f"{feature} requires Pro. Upgrade at /account.",
        )


async def check_portfolio_limit(user: AuthUser, current_count: int) -> None:
    if is_pro(user):
        return
    limit = get_settings().free_portfolio_limit
    if current_count >= limit:
        raise HTTPException(
            status_code=403,
            detail=f"Free tier portfolio limit ({limit} cards). Upgrade to Pro for unlimited.",
        )
