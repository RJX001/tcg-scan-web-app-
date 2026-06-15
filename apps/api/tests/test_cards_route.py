from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tcgscan_api.db.models import Game
from tcgscan_api.db.session import get_session
from tcgscan_api.main import app, fastapi_app
from tcgscan_api.repositories.cards import CardsRepo


@pytest.mark.asyncio
async def test_card_detail_route(sqlite_session: AsyncSession) -> None:
    cards = CardsRepo(sqlite_session)
    await cards.upsert_many(
        [{"game": Game.mtg, "name": "Black Lotus", "set_code": "LEA", "number": "232"}]
    )
    card = await cards.get_by_external(Game.mtg, "LEA", "232")
    assert card is not None

    async def override_session() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    fastapi_app.dependency_overrides[get_session] = override_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get(f"/v1/cards/{card.id}")
        assert r.status_code == 200
        assert r.json()["name"] == "Black Lotus"
    finally:
        fastapi_app.dependency_overrides.clear()
