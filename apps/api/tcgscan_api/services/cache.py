"""Redis cache helpers with stampede protection (best-effort)."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

import redis.asyncio as redis_async
import structlog

from tcgscan_api.config import get_settings

log = structlog.get_logger()


@lru_cache(maxsize=1)
def get_redis() -> redis_async.Redis:
    return redis_async.from_url(get_settings().redis_url, decode_responses=True)


async def cache_get(key: str) -> Any | None:
    try:
        raw = await get_redis().get(key)
    except Exception as exc:  # redis unreachable in local dev -> degrade gracefully
        log.warning("cache.get_failed", key=key, error=str(exc))
        return None
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        log.warning("cache.payload_invalid", key=key)
        return None


async def cache_set(key: str, value: Any, ttl_s: int = 900) -> None:
    try:
        await get_redis().set(key, json.dumps(value, default=str), ex=ttl_s)
    except Exception as exc:
        log.warning("cache.set_failed", key=key, error=str(exc))
