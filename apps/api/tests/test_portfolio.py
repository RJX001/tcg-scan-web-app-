from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from tcgscan_api.main import app


@pytest.mark.asyncio
async def test_portfolio_requires_auth_when_dev_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tcgscan_api.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("DEV_AUTH_ENABLED", "false")
    monkeypatch.delenv("CLERK_SECRET_KEY", raising=False)
    get_settings.cache_clear()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/v1/portfolio")
    assert r.status_code == 401
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_portfolio_dev_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    from tcgscan_api.config import get_settings
    from tcgscan_api.middleware.auth import AuthUser
    from tcgscan_api.routes import portfolio as portfolio_routes

    async def fake_list(*_a: object, **_k: object) -> list[object]:
        return []

    async def fake_resolve(_session: object, _request: object) -> AuthUser:
        import uuid

        return AuthUser(
            id=uuid.UUID("11111111-1111-4111-8111-111111111111"),
            clerk_id="test-user",
            tier="free",
            email=None,
        )

    monkeypatch.setattr(portfolio_routes, "list_portfolio", fake_list)
    monkeypatch.setattr(portfolio_routes, "resolve_db_user", fake_resolve)
    get_settings.cache_clear()
    monkeypatch.setenv("DEV_AUTH_ENABLED", "true")
    get_settings.cache_clear()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/v1/portfolio", headers={"X-Dev-User-Id": "test-user"})
    assert r.status_code == 200
    assert r.json() == []
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_card_search_route(monkeypatch: pytest.MonkeyPatch) -> None:
    from tcgscan_api.routes import cards as cards_routes
    from tcgscan_api.services.cards import CardOut

    async def fake_search(*_a: object, **_k: object) -> list[CardOut]:
        return [
            CardOut(
                id="1",
                slug="pokemon-base1-4-102",
                game="pokemon",
                name="Charizard",
                set_code="base1",
                number="4/102",
            )
        ]

    monkeypatch.setattr(cards_routes, "search_cards", fake_search)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/v1/cards/search", params={"q": "char"})
    assert r.status_code == 200
    assert r.json()[0]["name"] == "Charizard"
