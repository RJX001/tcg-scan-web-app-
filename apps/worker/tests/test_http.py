import httpx
import pytest
import respx

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
