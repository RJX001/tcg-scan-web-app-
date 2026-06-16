from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
import respx
from httpx import ASGITransport, AsyncClient, Response

from tcgscan_api.db.models import CardIdentity, Game, UserRole
from tcgscan_api.db.session import get_session
from tcgscan_api.main import app, fastapi_app
from tcgscan_api.middleware.auth import AuthUser
from tcgscan_api.repositories.cards import CardsRepo
from tcgscan_api.services.catalogue_ingest import run_catalogue_ingest
from tcgscan_api.services.catalogue_normalizer import to_card_identity_row
from tests.test_admin import _make_user, _patch_auth

OPTCG_CARD = {
    "card_name": "Perona",
    "set_name": "Romance Dawn",
    "set_id": "OP-01",
    "rarity": "UC",
    "card_set_id": "OP01-077",
    "card_color": "Blue",
    "card_type": "Character",
    "card_cost": "1",
    "card_power": "2000",
    "card_image": "https://optcgapi.com/media/static/Card_Images/OP01-077.jpg",
}


def _mock_one_piece_endpoints() -> None:
    respx.get("https://optcgapi.com/api/allSetCards/").mock(return_value=Response(200, json=[OPTCG_CARD]))
    respx.get("https://optcgapi.com/api/allSTCards/").mock(return_value=Response(200, json=[]))
    respx.get("https://optcgapi.com/api/allPromoCards/").mock(return_value=Response(200, json=[]))
    respx.get("https://optcgapi.com/api/allDonCards/").mock(return_value=Response(200, json=[]))


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
        AuthUser(id=user.id, supabase_user_id=user.supabase_user_id or "admin-user", tier="free", role="admin"),
    )
    return {"X-Dev-User-Id": "admin-user"}


def test_normalizer_handles_missing_optional_fields() -> None:
    row = to_card_identity_row(
        {
            "game": "one_piece",
            "source": "optcgapi",
            "source_card_id": "OP01-077",
            "name": "Perona",
        }
    )
    assert row["game"] == Game.one_piece
    assert row["source"] == "optcgapi"
    assert row["set_code"] is None
    assert row["attributes"] == {}


@pytest.mark.asyncio
@respx.mock
async def test_ingest_dry_run_does_not_write_db(sqlite_session: object) -> None:
    _mock_one_piece_endpoints()
    result = await run_catalogue_ingest(sqlite_session, "one_piece", limit=10, dry_run=True)
    assert result.dry_run is True
    assert result.inserted_count == 1
    cards = await CardsRepo(sqlite_session).search(q="Perona", limit=5)
    assert cards == []


@pytest.mark.asyncio
@respx.mock
async def test_ingest_sample_upserts_cards(sqlite_session: object) -> None:
    _mock_one_piece_endpoints()
    result = await run_catalogue_ingest(sqlite_session, "one_piece", limit=10, dry_run=False)
    assert result.status == "success"
    cards = await CardsRepo(sqlite_session).search(q="Perona", limit=5)
    assert len(cards) == 1
    assert cards[0].source == "optcgapi"
    assert cards[0].source_card_id == "OP01-077"


@pytest.mark.asyncio
async def test_card_search_returns_results(api_client: AsyncClient, sqlite_session: object) -> None:
    sqlite_session.add(
        CardIdentity(
            game=Game.pokemon,
            name="Pikachu",
            set_code="base1",
            number="58",
            source="pokemontcg",
            source_card_id="base1-58",
        )
    )
    await sqlite_session.commit()
    r = await api_client.get("/v1/cards/search", params={"q": "Pikachu"})
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["price_status"] == "pending"
    assert body[0]["current_value"] is None


@pytest.mark.asyncio
async def test_card_detail_price_pending(api_client: AsyncClient, sqlite_session: object) -> None:
    card = CardIdentity(
        game=Game.mtg,
        name="Lightning Bolt",
        set_code="LEA",
        number="161",
        source="scryfall",
        source_card_id="bolt-id",
    )
    sqlite_session.add(card)
    await sqlite_session.commit()
    await sqlite_session.refresh(card)
    r = await api_client.get(f"/v1/cards/{card.id}")
    assert r.status_code == 200
    body = r.json()
    assert body["price_status"] == "pending"
    assert body["listings_message"] == "Live listings pending marketplace source approval."


@pytest.mark.asyncio
@respx.mock
async def test_admin_ingest_requires_admin(api_client: AsyncClient, sqlite_session: object, monkeypatch: pytest.MonkeyPatch) -> None:
    user = await _make_user(sqlite_session, supabase_user_id="plain-user", role=UserRole.user)
    _patch_auth(
        monkeypatch,
        AuthUser(id=user.id, supabase_user_id=user.supabase_user_id or "plain-user", tier="free", role="user"),
    )
    r = await api_client.post("/v1/admin/sources/ingest/one-piece", headers={"X-Dev-User-Id": "plain-user"})
    assert r.status_code == 403


@pytest.mark.asyncio
@respx.mock
async def test_admin_ingest_one_piece(api_client: AsyncClient, admin_headers: dict[str, str]) -> None:
    _mock_one_piece_endpoints()
    r = await api_client.post("/v1/admin/sources/ingest/one-piece", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "success"
    assert body["inserted_count"] >= 1
    assert "source_run_id" in body
