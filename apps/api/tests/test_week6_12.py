from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from tcgscan_api.main import app
from tcgscan_api.services.digest import DigestPreviewOut


@pytest.mark.asyncio
async def test_digest_preview(monkeypatch: pytest.MonkeyPatch) -> None:
    from tcgscan_api.middleware.auth import AuthUser

    async def fake_resolve(_session: object, _request: object) -> AuthUser:
        import uuid

        return AuthUser(
            id=uuid.UUID("11111111-1111-4111-8111-111111111111"),
            supabase_user_id="dev-user",
            tier="pro",
            email=None,
        )

    async def fake_preview(_session: object, _auth: object) -> DigestPreviewOut:
        return DigestPreviewOut(
            subject="TCG Scan daily brief",
            body="Good morning — your portfolio has 2 cards tracked.",
            portfolio_count=2,
        )

    monkeypatch.setattr("tcgscan_api.routes.insights.resolve_db_user", fake_resolve)
    monkeypatch.setattr("tcgscan_api.routes.insights.preview_digest", fake_preview)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/v1/digest/preview", headers={"X-Dev-User-Id": "dev-user"})
    assert r.status_code == 200
    body = r.json()
    assert body["subject"] == "TCG Scan daily brief"
    assert body["portfolio_count"] == 2


@pytest.mark.asyncio
async def test_portfolio_export_csv(monkeypatch: pytest.MonkeyPatch) -> None:
    from tcgscan_api.middleware.auth import AuthUser
    from tcgscan_api.services.cards import CardOut
    from tcgscan_api.services.portfolio import PortfolioItemOut

    async def fake_resolve(_session: object, _request: object) -> AuthUser:
        import uuid

        return AuthUser(
            id=uuid.UUID("11111111-1111-4111-8111-111111111111"),
            supabase_user_id="dev-user",
            tier="pro",
            email=None,
        )

    async def fake_list(*_a: object, **_k: object) -> list[PortfolioItemOut]:
        card = CardOut(
            id="11111111-1111-4111-8111-111111111111",
            slug="pokemon-base1-4-102",
            game="pokemon",
            name="Charizard",
            set_code="base1",
            set_name="Base Set",
            number="4/102",
        )
        return [
            PortfolioItemOut(
                id="item-1",
                card=card,
                quantity=1,
                cost_basis_usd=200.0,
                estimated_value_usd=275.0,
            )
        ]

    monkeypatch.setattr("tcgscan_api.routes.portfolio.resolve_db_user", fake_resolve)
    monkeypatch.setattr("tcgscan_api.routes.portfolio.list_portfolio", fake_list)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/v1/portfolio/export", headers={"X-Dev-User-Id": "dev-user"})
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")
    assert "Charizard" in r.text
