from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from tcgscan_api.db.models import UserRole
from tcgscan_api.db.session import get_session
from tcgscan_api.main import app, fastapi_app
from tcgscan_api.middleware.auth import AuthUser
from tests.test_admin import _make_user, _patch_auth


@pytest_asyncio.fixture
async def api_client(sqlite_session: object) -> AsyncIterator[AsyncClient]:
    async def override_session() -> AsyncIterator[object]:
        yield sqlite_session

    fastapi_app.dependency_overrides[get_session] = override_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    fastapi_app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_sources_status_forbidden_for_user(
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
    r = await api_client.get("/v1/admin/sources/status", headers={"X-Dev-User-Id": "plain-user"})
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_sources_status_ok_for_admin(
    api_client: AsyncClient,
    sqlite_session: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    r = await api_client.get("/v1/admin/sources/status", headers={"X-Dev-User-Id": "admin-user"})
    assert r.status_code == 200
    body = r.json()
    assert "pricing_sources" in body
    assert "catalog_sources" in body
    catalog_ids = {row["id"] for row in body["catalog_sources"]}
    assert "dragon_ball_fusion_world" in catalog_ids
    assert "dragon_ball_masters" in catalog_ids
    assert body["architecture"]["api_sources_folder"] == "apps/api/tcgscan_api/sources/"


@pytest.mark.asyncio
async def test_sources_status_ok_when_catalog_stats_fail(
    api_client: AsyncClient,
    sqlite_session: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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

    async def _boom(_session: object) -> dict[str, object]:
        raise RuntimeError("catalog stats unavailable")

    monkeypatch.setattr(
        "tcgscan_api.services.admin_sources_status.catalogue_stats",
        _boom,
    )
    r = await api_client.get("/v1/admin/sources/status", headers={"X-Dev-User-Id": "admin-user"})
    assert r.status_code == 200
    body = r.json()
    assert "catalog_stats" in body
    assert body["catalog_stats"]
    assert "catalog_stats_degraded" in body.get("status_warnings", [])


@pytest.mark.asyncio
async def test_sources_status_ok_when_ebay_stats_fail(
    api_client: AsyncClient,
    sqlite_session: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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

    async def _boom(_session: object) -> dict[str, object]:
        raise RuntimeError("marketplace_listings missing")

    monkeypatch.setattr(
        "tcgscan_api.services.admin_sources_status.ebay_listing_stats",
        _boom,
    )
    r = await api_client.get("/v1/admin/sources/status", headers={"X-Dev-User-Id": "admin-user"})
    assert r.status_code == 200
    body = r.json()
    assert "pricing_stats" in body
    assert body["pricing_stats"][0]["source_key"] == "ebay"
    assert body["pricing_stats"][0]["listing_count"] == 0
    assert "ebay_stats_unavailable" in body.get("status_warnings", [])


@pytest.mark.asyncio
async def test_sources_status_empty_source_runs(
    api_client: AsyncClient,
    sqlite_session: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    r = await api_client.get("/v1/admin/sources/status", headers={"X-Dev-User-Id": "admin-user"})
    assert r.status_code == 200
    body = r.json()
    for row in body.get("catalog_stats", []):
        assert row["last_success_at"] is None
        assert row["card_count"] == 0


@pytest.mark.asyncio
async def test_sources_test_reddit_not_implemented(
    api_client: AsyncClient,
    sqlite_session: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    r = await api_client.get(
        "/v1/admin/sources/test/reddit", headers={"X-Dev-User-Id": "admin-user"}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "not_implemented"
    assert body["implementation"] == "missing"
