from __future__ import annotations

from collections.abc import AsyncIterator
from decimal import Decimal

import pytest
import pytest_asyncio
import respx
from httpx import ASGITransport, AsyncClient, Response

from tcgscan_api.config import get_settings
from tcgscan_api.db.models import MarketplaceListing, UserRole
from tcgscan_api.db.session import get_session
from tcgscan_api.main import app, fastapi_app
from tcgscan_api.middleware.auth import AuthUser
from tcgscan_api.repositories.marketplace_listings import MarketplaceListingsRepo
from tcgscan_api.services.ebay_ingest import run_ebay_ingest
from tcgscan_api.services.ebay_normalizer import normalize_ebay_item_summary
from tcgscan_api.services.source_audit import build_sources_status
from tests.test_admin import _make_user, _patch_auth

EBAY_ITEM = {
    "itemId": "v1|123456789|0",
    "title": "PSA 10 Charizard Base Set Pokemon Card",
    "itemWebUrl": "https://www.ebay.co.uk/itm/123456789",
    "price": {"value": "199.99", "currency": "GBP"},
    "condition": "Graded",
    "image": {"imageUrl": "https://i.ebayimg.com/images/g/abc/s-l500.jpg"},
    "seller": {"username": "tcg_seller_uk"},
}

OAUTH_RESPONSE = {"access_token": "test-token", "expires_in": 7200}
SEARCH_RESPONSE = {"itemSummaries": [EBAY_ITEM]}


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest_asyncio.fixture
async def api_client(sqlite_session: object) -> AsyncIterator[AsyncClient]:
    async def override_session() -> AsyncIterator[object]:
        yield sqlite_session

    fastapi_app.dependency_overrides[get_session] = override_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    fastapi_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_headers(
    sqlite_session: object,
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, str]:
    user = await _make_user(sqlite_session, supabase_user_id="admin-user", role=UserRole.admin)
    _patch_auth(
        monkeypatch,
        AuthUser(
            id=user.id,
            supabase_user_id=user.supabase_user_id or "admin-user",
            tier="free",
            role="admin",
        ),
    )
    return {"X-Dev-User-Id": "admin-user"}


def test_ebay_config_shows_connected_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EBAY_APP_ID", "app")
    monkeypatch.setenv("EBAY_CERT_ID", "cert")
    get_settings.cache_clear()
    status = build_sources_status()
    ebay = next(s for s in status["pricing_sources"] if s["id"] == "ebay")
    assert ebay["implementation"] == "connected"
    assert ebay["configured"] is True


def test_normalize_ebay_item_summary() -> None:
    row = normalize_ebay_item_summary(EBAY_ITEM, marketplace="EBAY_GB")
    assert row is not None
    assert row["source"] == "ebay"
    assert row["source_listing_id"] == "v1|123456789|0"
    assert row["title"].startswith("PSA 10 Charizard")
    assert row["price"] == Decimal("199.99")
    assert row["currency"] == "GBP"
    assert row["listing_status"] == "active"
    assert row["affiliate_status"] == "not_configured"
    assert row["seller_username"] == "tcg_seller_uk"


def test_normalize_applies_affiliate_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EBAY_AFFILIATE_TRACKING_ID", "track123")
    monkeypatch.setenv("EBAY_AFFILIATE_CAMPAIGN_ID", "camp456")
    get_settings.cache_clear()
    row = normalize_ebay_item_summary(EBAY_ITEM, marketplace="EBAY_GB")
    assert row is not None
    assert row["affiliate_status"] == "configured"
    assert "campid=camp456" in row["item_url"]
    assert "customid=track123" in row["item_url"]


@pytest.mark.asyncio
async def test_upsert_without_duplicates(sqlite_session: object) -> None:
    row = normalize_ebay_item_summary(EBAY_ITEM, marketplace="EBAY_GB")
    assert row is not None
    repo = MarketplaceListingsRepo(sqlite_session)
    ins1, upd1, _ = await repo.upsert_batch([row])
    assert ins1 == 1 and upd1 == 0
    ins2, upd2, _ = await repo.upsert_batch([row])
    assert ins2 == 0 and upd2 == 1
    count = await repo.count_active(source="ebay")
    assert count == 1


@pytest.mark.asyncio
@respx.mock
async def test_ebay_ingest_normalises_mocked_browse(
    sqlite_session: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EBAY_APP_ID", "app")
    monkeypatch.setenv("EBAY_CERT_ID", "cert")
    get_settings.cache_clear()
    respx.post("https://api.ebay.com/identity/v1/oauth2/token").mock(
        return_value=Response(200, json=OAUTH_RESPONSE)
    )
    respx.get("https://api.ebay.com/buy/browse/v1/item_summary/search").mock(
        return_value=Response(200, json=SEARCH_RESPONSE)
    )
    result = await run_ebay_ingest(sqlite_session, query="charizard", limit=25, dry_run=False)
    assert result.status == "success"
    assert result.inserted_count == 1
    listings = await MarketplaceListingsRepo(sqlite_session).browse(source="ebay")
    assert len(listings) == 1
    assert listings[0].title.startswith("PSA 10 Charizard")


@pytest.mark.asyncio
async def test_ebay_ingest_missing_env_returns_missing_env(sqlite_session: object) -> None:
    result = await run_ebay_ingest(sqlite_session, dry_run=False)
    assert result.status == "missing_env"
    assert result.inserted_count == 0


@pytest.mark.asyncio
async def test_ebay_ingest_route_requires_admin(
    api_client: AsyncClient,
    sqlite_session: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = await _make_user(sqlite_session, supabase_user_id="plain-user", role=UserRole.user)
    _patch_auth(
        monkeypatch,
        AuthUser(
            id=user.id,
            supabase_user_id=user.supabase_user_id or "plain-user",
            tier="free",
            role="user",
        ),
    )
    r = await api_client.post(
        "/v1/admin/sources/ingest/ebay", headers={"X-Dev-User-Id": "plain-user"}
    )
    assert r.status_code == 403


@pytest.mark.asyncio
@respx.mock
async def test_ebay_ingest_route_admin_ok(
    api_client: AsyncClient,
    admin_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EBAY_APP_ID", "app")
    monkeypatch.setenv("EBAY_CERT_ID", "cert")
    get_settings.cache_clear()
    respx.post("https://api.ebay.com/identity/v1/oauth2/token").mock(
        return_value=Response(200, json=OAUTH_RESPONSE)
    )
    respx.get("https://api.ebay.com/buy/browse/v1/item_summary/search").mock(
        return_value=Response(200, json=SEARCH_RESPONSE)
    )
    r = await api_client.post(
        "/v1/admin/sources/ingest/ebay",
        params={"query": "pokemon card charizard", "limit": 25},
        headers=admin_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "success"
    assert "test-token" not in str(body)


@pytest.mark.asyncio
async def test_shop_empty_without_listings(api_client: AsyncClient) -> None:
    r = await api_client.get("/v1/market/listings")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_shop_displays_stored_ebay_listings(
    api_client: AsyncClient,
    sqlite_session: object,
) -> None:
    sqlite_session.add(
        MarketplaceListing(
            source="ebay",
            source_listing_id="v1|999|0",
            title="Pikachu Promo eBay Listing",
            price=Decimal("12.50"),
            currency="GBP",
            item_url="https://www.ebay.co.uk/itm/999",
            marketplace="EBAY_GB",
            listing_status="active",
        )
    )
    await sqlite_session.commit()
    r = await api_client.get("/v1/market/listings", params={"source": "ebay"})
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["title"] == "Pikachu Promo eBay Listing"
    assert body[0]["source"] == "ebay"
    assert body[0]["listing_url"] == "https://www.ebay.co.uk/itm/999"
    assert body[0]["card"] is None
