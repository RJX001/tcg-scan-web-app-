"""User role guards for admin API surface."""

from __future__ import annotations

from fastapi import HTTPException

from tcgscan_api.middleware.auth import AuthUser

_LEVELS = {"user": 0, "admin": 1, "admin_senior": 2, "owner": 3}


def _level(user: AuthUser) -> int:
    return _LEVELS.get(user.role, 0)


def require_admin(user: AuthUser) -> None:
    """admin and above — view-only monitoring surface."""
    if _level(user) < 1:
        raise HTTPException(status_code=403, detail="Admin access required")


def require_senior(user: AuthUser) -> None:
    """admin_senior and above — comp tiers, support/moderation, view revenue."""
    if _level(user) < 2:
        raise HTTPException(status_code=403, detail="Senior admin access required")


def require_owner(user: AuthUser) -> None:
    """owner only — grant/change roles, edit account numbers."""
    if _level(user) < 3:
        raise HTTPException(status_code=403, detail="Owner access required")
