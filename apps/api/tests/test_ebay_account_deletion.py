from __future__ import annotations

import hashlib

import pytest
from httpx import ASGITransport, AsyncClient

from tcgscan_api.config import get_settings
from tcgscan_api.main import app
from tcgscan_api.services.ebay_account_deletion import (
    DEFAULT_ENDPOINT_URL,
    compute_challenge_response,
)

TOKEN = "CardChartProduction_2026_Verify_Token"
CHALLENGE = "test-challenge-12345"


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def ebay_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EBAY_ACCOUNT_DELETION_VERIFICATION_TOKEN", TOKEN)
    monkeypatch.setenv("EBAY_ACCOUNT_DELETION_ENDPOINT_URL", DEFAULT_ENDPOINT_URL)
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_challenge_returns_correct_response(ebay_env: None) -> None:
    expected = compute_challenge_response(CHALLENGE, TOKEN, DEFAULT_ENDPOINT_URL)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/v1/ebay/account-deletion", params={"challenge_code": CHALLENGE})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")
    assert r.json() == {"challengeResponse": expected}
    assert TOKEN not in r.text


@pytest.mark.asyncio
async def test_challenge_missing_code_returns_400(ebay_env: None) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/v1/ebay/account-deletion")
    assert r.status_code == 400
    assert "challenge_code" in r.json()["detail"]


@pytest.mark.asyncio
async def test_challenge_missing_token_returns_500(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EBAY_ACCOUNT_DELETION_VERIFICATION_TOKEN", raising=False)
    get_settings.cache_clear()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/v1/ebay/account-deletion", params={"challenge_code": CHALLENGE})
    assert r.status_code == 500
    body = r.json()
    assert TOKEN not in str(body)
    assert "configured" in body["detail"].lower()


@pytest.mark.asyncio
async def test_post_notification_returns_204(ebay_env: None) -> None:
    payload = {
        "metadata": {"topic": "MARKETPLACE_ACCOUNT_DELETION"},
        "notification": {
            "notificationId": "notif-1",
            "eventDate": "2026-06-16T12:00:00Z",
            "data": {"userId": "ebay-user-1", "eiasToken": "token-abc"},
        },
    }
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/v1/ebay/account-deletion", json=payload)
    assert r.status_code == 204
    assert TOKEN not in (r.text or "")


@pytest.mark.asyncio
async def test_route_does_not_require_auth(ebay_env: None) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get(
            "/v1/ebay/account-deletion",
            params={"challenge_code": CHALLENGE},
            headers={"Authorization": "Bearer invalid-token"},
        )
    assert r.status_code == 200


def test_compute_challenge_response_matches_ebay_spec() -> None:
    digest = compute_challenge_response("abc", "token", DEFAULT_ENDPOINT_URL)
    expected = hashlib.sha256(f"abctoken{DEFAULT_ENDPOINT_URL}".encode()).hexdigest()
    assert digest == expected
