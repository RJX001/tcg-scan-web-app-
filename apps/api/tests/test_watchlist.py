from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tcgscan_api.db.models import Game
from tcgscan_api.db.session import get_session
from tcgscan_api.main import app
from tcgscan_api.middleware.auth import AuthUser
from tcgscan_api.repositories.cards import CardsRepo
from tcgscan_api.repositories.users import UsersRepo


async def _setup(
    sqlite_session: AsyncSession, monkeypatch: pytest.MonkeyPatch, *, tier: str
) -> tuple[AsyncClient, str]:
    cards = CardsRepo(sqlite_session)
    await cards.upsert_many(
        [{"game": Game.pokemon, "name": "Charizard", "set_code": "base1", "number": "4/102"}]
    )
    card = await cards.get_by_external(Game.pokemon, "base1", "4/102")
    assert card is not None
    user = await UsersRepo(sqlite_session).get_or_create(supabase_user_id="dev-user")

    async def fake_resolve(_session: object, _request: object) -> AuthUser:
        return AuthUser(id=user.id, supabase_user_id="dev-user", tier=tier, email=None)

    monkeypatch.setattr("tcgscan_api.routes.watchlist.resolve_db_user", fake_resolve)

    async def override_session() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    app.dependency_overrides[get_session] = override_session
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    return client, str(card.id)


@pytest.mark.asyncio
async def test_watchlist_crud(
    sqlite_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, card_id = await _setup(sqlite_session, monkeypatch, tier="pro")
    try:
        async with client:
            r = await client.post("/v1/watchlist", json={"card_id": card_id})
            assert r.status_code == 201
            assert r.json()["card"]["name"] == "Charizard"

            # adding twice is idempotent
            r = await client.post("/v1/watchlist", json={"card_id": card_id})
            assert r.status_code == 201

            r = await client.get("/v1/watchlist")
            assert r.status_code == 200
            items = r.json()
            assert len(items) == 1

            r = await client.delete(f"/v1/watchlist/{items[0]['id']}")
            assert r.status_code == 204
            r = await client.get("/v1/watchlist")
            assert r.json() == []
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_watchlist_requires_pro(
    sqlite_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, card_id = await _setup(sqlite_session, monkeypatch, tier="free")
    try:
        async with client:
            r = await client.post("/v1/watchlist", json={"card_id": card_id})
            assert r.status_code == 403

            r = await client.get("/v1/watchlist")
            assert r.status_code == 200
            assert r.json() == []
    finally:
        app.dependency_overrides.clear()
