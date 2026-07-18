import httpx
import pytest
import respx
from structlog.testing import capture_logs

from tcgscan_worker.http import (
    CircuitBreaker,
    CircuitOpenError,
    ResilientClient,
    TokenBucket,
)


@pytest.mark.asyncio
async def test_token_bucket_refills() -> None:
    bucket = TokenBucket(rate_per_sec=100.0, burst=2)
    await bucket.acquire()
    await bucket.acquire()


def test_circuit_breaker_opens_and_resets() -> None:
    cb = CircuitBreaker(failure_threshold=2, reset_after_s=60.0)
    cb.record_failure()
    cb.record_failure()
    with pytest.raises(CircuitOpenError):
        cb.check()
    cb.record_success()
    cb.check()  # no exception after success


@pytest.mark.asyncio
async def test_resilient_client_retries_then_succeeds() -> None:
    route = respx.MockRouter(assert_all_called=False)
    route.get("https://api.example.com/v1/cards").mock(
        side_effect=[
            httpx.Response(500),
            httpx.Response(200, json={"name": "Charizard"}),
        ]
    )
    with route:
        client = ResilientClient(rate_per_sec=100, burst=10, max_attempts=3)
        try:
            out = await client.get_json("https://api.example.com/v1/cards")
            assert out["name"] == "Charizard"
        finally:
            await client.aclose()


@pytest.mark.asyncio
async def test_fail_twice_succeed_logs_retry_warnings_only() -> None:
    route = respx.MockRouter(assert_all_called=False)
    route.get("https://api.example.com/v1/cards").mock(
        side_effect=[
            httpx.Response(500),
            httpx.Response(502),
            httpx.Response(200, json={"ok": True}),
        ]
    )
    with route, capture_logs() as logs:
        client = ResilientClient(rate_per_sec=100, burst=10, max_attempts=4)
        try:
            out = await client.get_json("https://api.example.com/v1/cards")
            assert out["ok"] is True
        finally:
            await client.aclose()

    retries = [e for e in logs if e["event"] == "http.retry"]
    assert len(retries) == 2
    assert all(e["log_level"] == "warning" for e in retries)
    assert [e["attempt"] for e in retries] == [1, 2]
    assert all(e["max_attempts"] == 4 for e in retries)
    assert not any(e["event"] == "http.exhausted" for e in logs)
    assert not any(e["log_level"] == "error" for e in logs)


@pytest.mark.asyncio
async def test_always_fail_logs_retries_then_exhausted() -> None:
    route = respx.MockRouter(assert_all_called=False)
    route.get("https://api.example.com/v1/cards").mock(return_value=httpx.Response(500))
    with route, capture_logs() as logs:
        client = ResilientClient(rate_per_sec=100, burst=10, max_attempts=3)
        try:
            with pytest.raises(httpx.HTTPStatusError):
                await client.get_json("https://api.example.com/v1/cards")
        finally:
            await client.aclose()

    retries = [e for e in logs if e["event"] == "http.retry"]
    exhausted = [e for e in logs if e["event"] == "http.exhausted"]
    assert len(retries) == 2
    assert all(e["log_level"] == "warning" for e in retries)
    assert [e["attempt"] for e in retries] == [1, 2]
    assert len(exhausted) == 1
    assert exhausted[0]["log_level"] == "error"
    assert exhausted[0]["attempts"] == 3


def test_circuit_open_logged_once_on_transition() -> None:
    with capture_logs() as logs:
        cb = CircuitBreaker(failure_threshold=2, reset_after_s=30.0)
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()  # already open — no second transition log

    opens = [e for e in logs if e["event"] == "http.circuit_open"]
    assert len(opens) == 1
    assert opens[0]["log_level"] == "error"
    assert opens[0]["failures"] == 2
    assert opens[0]["cooldown_s"] == 30.0


def test_circuit_reject_logs_debug() -> None:
    cb = CircuitBreaker(failure_threshold=1, reset_after_s=60.0)
    cb.record_failure()
    with capture_logs() as logs:
        with pytest.raises(CircuitOpenError):
            cb.check()

    rejects = [e for e in logs if e["event"] == "http.circuit_reject"]
    assert len(rejects) == 1
    assert rejects[0]["log_level"] == "debug"


def test_circuit_closed_logged_on_success_reset() -> None:
    cb = CircuitBreaker(failure_threshold=1, reset_after_s=60.0)
    cb.record_failure()
    with capture_logs() as logs:
        cb.record_success()

    closed = [e for e in logs if e["event"] == "http.circuit_closed"]
    assert len(closed) == 1
    assert closed[0]["log_level"] == "info"
