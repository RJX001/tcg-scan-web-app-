from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tcgscan_api.db.session import get_session
from tcgscan_api.main import app
from tcgscan_api.middleware.auth import AuthUser
from tcgscan_api.repositories.users import UsersRepo


async def _client_for(
    sqlite_session: AsyncSession, monkeypatch: pytest.MonkeyPatch, *, tier: str
) -> AsyncClient:
    user = await UsersRepo(sqlite_session).get_or_create(clerk_id="dev-user")

    async def fake_resolve(_session: object, _request: object) -> AuthUser:
        return AuthUser(id=user.id, clerk_id="dev-user", tier=tier, email=None)

    monkeypatch.setattr("tcgscan_api.routes.searches.resolve_db_user", fake_resolve)

    async def override_session() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    app.dependency_overrides[get_session] = override_session
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_saved_search_crud(
    sqlite_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = await _client_for(sqlite_session, monkeypatch, tier="pro")
    try:
        async with client:
            body = {"name": "Pokemon gainers", "params": {"game": "pokemon", "sort": "change"}}
            r = await client.post("/v1/searches", json=body)
            assert r.status_code == 201
            created = r.json()
            assert created["name"] == "Pokemon gainers"
            assert created["params"]["game"] == "pokemon"

            # Same name upserts (params replaced) instead of duplicating
            r = await client.post(
                "/v1/searches",
                json={"name": "Pokemon gainers", "params": {"game": "pokemon", "sort": "price"}},
            )
            assert r.status_code == 201

            r = await client.get("/v1/searches")
            assert r.status_code == 200
            items = r.json()
            assert len(items) == 1
            assert items[0]["params"]["sort"] == "price"

            r = await client.delete(f"/v1/searches/{items[0]['id']}")
            assert r.status_code == 204
            r = await client.get("/v1/searches")
            assert r.json() == []

            # Unknown params rejected
            r = await client.post("/v1/searches", json={"name": "bad", "params": {"bogus": "x"}})
            assert r.status_code == 422
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_saved_search_requires_pro(
    sqlite_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = await _client_for(sqlite_session, monkeypatch, tier="free")
    try:
        async with client:
            r = await client.post("/v1/searches", json={"name": "n", "params": {"game": "pokemon"}})
            assert r.status_code == 403

            r = await client.get("/v1/searches")
            assert r.status_code == 200
            assert r.json() == []
    finally:
        app.dependency_overrides.clear()
