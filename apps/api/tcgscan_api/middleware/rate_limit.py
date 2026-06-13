"""Redis token-bucket rate limiting for scan endpoint."""

from __future__ import annotations

from datetime import UTC, datetime

import redis.asyncio as redis
from fastapi import HTTPException, Request

from tcgscan_api.config import get_settings
from tcgscan_api.db.session import get_sessionmaker
from tcgscan_api.repositories.users import UsersRepo
from tcgscan_api.db.models import UserTier


async def _redis() -> redis.Redis:  # type: ignore[type-arg]
    settings = get_settings()
    return redis.from_url(settings.redis_url, decode_responses=True)


async def _load_tier_for_clerk(clerk_id: str, email: str | None) -> str:
    async with get_sessionmaker()() as session:
        db_user = await UsersRepo(session).get_or_create(clerk_id=clerk_id, email=email)
        tier = db_user.tier
        return tier.value if isinstance(tier, UserTier) else str(tier)


async def check_scan_rate_limit(request: Request) -> None:
    settings = get_settings()
    user = getattr(request.state, "user", None)
    if user:
        tier = await _load_tier_for_clerk(user.clerk_id, getattr(user, "email", None))
        if tier == UserTier.pro.value or tier == "pro":
            return

    client_ip = request.client.host if request.client else "unknown"
    key_id = str(getattr(user, "clerk_id", None) or client_ip)
    day = datetime.now(UTC).strftime("%Y-%m-%d")
    key = f"scan_rate:{key_id}:{day}"

    try:
        r = await _redis()
        count = await r.incr(key)
        if count == 1:
            await r.expire(key, 86400)
        if count > settings.free_scans_per_day:
            raise HTTPException(
                status_code=429,
                detail=f"Free tier limit: {settings.free_scans_per_day} scans/day. Upgrade to Pro.",
            )
    except HTTPException:
        raise
    except Exception:
        pass


async def check_ip_rate_limit(
    request: Request,
    *,
    prefix: str,
    limit: int,
    window_s: int = 60,
) -> None:
    """Per-IP token bucket for anonymous public endpoints (search, etc.)."""
    client_ip = request.client.host if request.client else "unknown"
    key = f"{prefix}:{client_ip}"

    try:
        r = await _redis()
        count = await r.incr(key)
        if count == 1:
            await r.expire(key, window_s)
        if count > limit:
            raise HTTPException(status_code=429, detail="Too many requests. Try again shortly.")
    except HTTPException:
        raise
    except Exception:
        pass
