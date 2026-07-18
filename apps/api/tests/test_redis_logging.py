"""Redis degradation paths must log WARNING events (fail-open / cache miss)."""

from __future__ import annotations

import pytest
from structlog.testing import capture_logs
from starlette.requests import Request

from tcgscan_api.middleware import rate_limit as rate_limit_mod
from tcgscan_api.services import cache as cache_mod


class _FailingRedis:
    async def get(self, _key: str) -> str:
        raise ConnectionError("redis unreachable")

    async def set(self, _key: str, _value: str, *, ex: int | None = None) -> None:
        raise ConnectionError("redis unreachable")

    async def incr(self, _key: str) -> int:
        raise ConnectionError("redis unreachable")


class _InvalidPayloadRedis:
    async def get(self, _key: str) -> str:
        return "not-valid-json{{"


def _http_request(*, client_host: str = "127.0.0.1") -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "query_string": b"",
            "client": (client_host, 12345),
        }
    )


def _warning_events(cap: list[dict[str, object]], event: str) -> list[dict[str, object]]:
    return [
        entry
        for entry in cap
        if entry.get("event") == event and entry.get("log_level") == "warning"
    ]


@pytest.mark.asyncio
async def test_cache_get_redis_failure_logs_warning_and_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache_mod.get_redis.cache_clear()
    monkeypatch.setattr(cache_mod, "get_redis", lambda: _FailingRedis())

    with capture_logs() as cap:
        result = await cache_mod.cache_get("test:key")

    assert result is None
    events = _warning_events(cap, "cache.get_failed")
    assert len(events) == 1
    assert events[0]["key"] == "test:key"
    assert "redis unreachable" in events[0]["error"]


@pytest.mark.asyncio
async def test_cache_set_redis_failure_logs_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache_mod.get_redis.cache_clear()
    monkeypatch.setattr(cache_mod, "get_redis", lambda: _FailingRedis())

    with capture_logs() as cap:
        await cache_mod.cache_set("test:key", {"foo": "bar"})

    events = _warning_events(cap, "cache.set_failed")
    assert len(events) == 1
    assert events[0]["key"] == "test:key"
    assert "redis unreachable" in events[0]["error"]


@pytest.mark.asyncio
async def test_cache_get_invalid_payload_logs_warning_and_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache_mod.get_redis.cache_clear()
    monkeypatch.setattr(cache_mod, "get_redis", lambda: _InvalidPayloadRedis())

    with capture_logs() as cap:
        result = await cache_mod.cache_get("test:key")

    assert result is None
    events = _warning_events(cap, "cache.payload_invalid")
    assert len(events) == 1
    assert events[0]["key"] == "test:key"


@pytest.mark.asyncio
async def test_scan_rate_limit_fail_open_logs_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def failing_redis() -> _FailingRedis:
        return _FailingRedis()

    monkeypatch.setattr(rate_limit_mod, "_redis", failing_redis)

    request = _http_request()
    request.state.user = None

    with capture_logs() as cap:
        await rate_limit_mod.check_scan_rate_limit(request)

    events = _warning_events(cap, "rate_limit.fail_open")
    assert len(events) == 1
    assert events[0]["scope"] == "scan"
    assert "redis unreachable" in events[0]["error"]


@pytest.mark.asyncio
async def test_ip_rate_limit_fail_open_logs_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def failing_redis() -> _FailingRedis:
        return _FailingRedis()

    monkeypatch.setattr(rate_limit_mod, "_redis", failing_redis)

    request = _http_request()

    with capture_logs() as cap:
        await rate_limit_mod.check_ip_rate_limit(request, prefix="search", limit=10)

    events = _warning_events(cap, "rate_limit.fail_open")
    assert len(events) == 1
    assert events[0]["scope"] == "ip"
    assert "redis unreachable" in events[0]["error"]
