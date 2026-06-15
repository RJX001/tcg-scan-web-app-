"""Shared async HTTP client for TCG source adapters."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx
import structlog
from tenacity import (
    AsyncRetrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from tcgscan_api.services.cache import cache_get, cache_set

log = structlog.get_logger()

USER_AGENT = "CardChart/1.0 contact@cardchart.co.uk"
DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json",
}


def _should_retry(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in {429, 500, 502, 503, 504}
    return False


class _TokenBucket:
    def __init__(self, rate_per_sec: float, burst: int) -> None:
        self._rate = rate_per_sec
        self._burst = float(burst)
        self._tokens = float(burst)
        self._last = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            while True:
                now = time.monotonic()
                elapsed = now - self._last
                self._tokens = min(self._burst, self._tokens + elapsed * self._rate)
                self._last = now
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
                await asyncio.sleep(max(0.05, (1.0 - self._tokens) / max(self._rate, 0.01)))


class SourceHttpClient:
    """Rate-limited HTTP client with retry/backoff and optional Redis cache."""

    def __init__(
        self,
        *,
        base_url: str = "",
        rate_per_sec: float = 2.0,
        burst: int = 4,
        timeout_s: float = 20.0,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._bucket = _TokenBucket(rate_per_sec, burst)
        merged = dict(DEFAULT_HEADERS)
        if headers:
            merged.update(headers)
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=timeout_s,
            headers=merged,
            follow_redirects=True,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get_json(
        self,
        path: str,
        *,
        params: dict[str, str | int] | None = None,
        cache_key: str | None = None,
        cache_ttl_s: int = 900,
    ) -> Any:
        if cache_key:
            cached = await cache_get(cache_key)
            if cached is not None:
                return cached

        await self._bucket.acquire()
        payload: Any = None
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(4),
            wait=wait_exponential_jitter(initial=0.5, max=8.0),
            retry=retry_if_exception(_should_retry),
            reraise=True,
        ):
            with attempt:
                resp = await self._client.get(path, params=params)
                resp.raise_for_status()
                payload = resp.json()

        if cache_key and payload is not None:
            await cache_set(cache_key, payload, ttl_s=cache_ttl_s)
        return payload

    async def head_ok(self, url: str) -> bool:
        await self._bucket.acquire()
        try:
            resp = await self._client.head(url)
            return resp.status_code < 400
        except httpx.HTTPError:
            return False

    async def get_text(self, path: str, *, accept: str = "text/html") -> tuple[int, str, str]:
        await self._bucket.acquire()
        resp = await self._client.get(path, headers={"Accept": accept})
        return resp.status_code, str(resp.url), resp.text

    async def probe_json_url(self, url: str) -> tuple[bool, Any | None]:
        await self._bucket.acquire()
        try:
            resp = await self._client.get(url, headers={"Accept": "application/json"})
            if resp.status_code != 200:
                return False, None
            content_type = resp.headers.get("content-type", "")
            if "json" not in content_type.lower():
                return False, None
            data = resp.json()
            return True, data
        except httpx.HTTPError:
            return False, None
