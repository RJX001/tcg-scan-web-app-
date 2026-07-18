from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

import httpx
import structlog
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

log = structlog.get_logger()


class CircuitOpenError(RuntimeError):
    """Raised when too many failures have tripped the circuit breaker."""


@dataclass
class TokenBucket:
    rate_per_sec: float
    burst: int
    _tokens: float = 0.0
    _last_refill: float = 0.0

    def __post_init__(self) -> None:
        self._tokens = float(self.burst)
        self._last_refill = time.monotonic()

    async def acquire(self) -> None:
        while True:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(float(self.burst), self._tokens + elapsed * self.rate_per_sec)
            self._last_refill = now
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return
            await asyncio.sleep(max(0.01, (1.0 - self._tokens) / max(self.rate_per_sec, 0.01)))


@dataclass
class CircuitBreaker:
    failure_threshold: int = 5
    reset_after_s: float = 30.0
    _failures: int = 0
    _opened_at: float | None = None

    def record_success(self) -> None:
        was_open = self._opened_at is not None
        self._failures = 0
        self._opened_at = None
        if was_open:
            log.info("http.circuit_closed")

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self.failure_threshold and self._opened_at is None:
            self._opened_at = time.monotonic()
            log.error(
                "http.circuit_open",
                failures=self._failures,
                cooldown_s=self.reset_after_s,
            )

    def check(self) -> None:
        if self._opened_at is None:
            return
        if time.monotonic() - self._opened_at >= self.reset_after_s:
            self._failures = 0
            self._opened_at = None
            log.info("http.circuit_closed")
            return
        log.debug(
            "http.circuit_reject",
            failures=self._failures,
            cooldown_s=self.reset_after_s,
        )
        raise CircuitOpenError("circuit open")


class ResilientClient:
    """Async HTTP client with retries, token-bucket rate limit, and circuit breaker."""

    def __init__(
        self,
        *,
        base_url: str = "",
        rate_per_sec: float = 5.0,
        burst: int = 10,
        timeout_s: float = 10.0,
        headers: Mapping[str, str] | None = None,
        max_attempts: int = 4,
    ) -> None:
        self._bucket = TokenBucket(rate_per_sec=rate_per_sec, burst=burst)
        self._breaker = CircuitBreaker()
        self._max_attempts = max_attempts
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout_s,
            headers=dict(headers or {}),
            follow_redirects=True,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get_json(self, url: str, **kwargs: Any) -> dict[str, Any]:
        return await self._request("GET", url, **kwargs)

    async def post_json(self, url: str, **kwargs: Any) -> dict[str, Any]:
        return await self._request("POST", url, **kwargs)

    async def _request(self, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        self._breaker.check()
        await self._bucket.acquire()

        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(self._max_attempts),
            wait=wait_exponential_jitter(initial=0.5, max=10.0),
            retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TransportError)),
            reraise=True,
        ):
            with attempt:
                try:
                    r = await self._client.request(method, url, **kwargs)
                    r.raise_for_status()
                    payload = r.json()
                    self._breaker.record_success()
                    return payload if isinstance(payload, dict) else {"data": payload}
                except (httpx.HTTPStatusError, httpx.TransportError) as exc:
                    self._breaker.record_failure()
                    attempt_number = attempt.retry_state.attempt_number
                    if attempt_number < self._max_attempts:
                        log.warning(
                            "http.retry",
                            method=method,
                            url=url,
                            attempt=attempt_number,
                            max_attempts=self._max_attempts,
                            error=str(exc),
                        )
                    else:
                        log.error(
                            "http.exhausted",
                            method=method,
                            url=url,
                            attempts=self._max_attempts,
                            error=str(exc),
                        )
                    raise

        raise RuntimeError("unreachable")


@asynccontextmanager
async def resilient_client(**kwargs: Any) -> AsyncIterator[ResilientClient]:
    client = ResilientClient(**kwargs)
    try:
        yield client
    finally:
        await client.aclose()
