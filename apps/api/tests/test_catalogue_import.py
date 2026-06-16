from __future__ import annotations

import uuid
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
from tcgscan_api.repositories.source_runs import SourceRunsRepo
from tcgscan_api.services.catalogue_import import execute_full_catalogue_import, start_full_catalogue_import
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

POKEMON_PAGE = {
    "data": [
        {
            "id": "base1-4",
            "name": "Charizard",
            "number": "4",
            "rarity": "Rare Holo",
            "set": {"id": "base1", "name": "Base", "ptcgoCode": "BS"},
            "images": {"large": "https://images.pokemontcg.io/base1/4_hires.png"},
            "supertype": "Pokémon",
            "types": ["Fire"],
        }
    ],
    "page": 1,
    "pageSize": 250,
    "count": 1,
    "totalCount": 1,
}

SCRYFALL_PAGE = {
    "object": "list",
    "has_more": False,
    "data": [
        {
            "id": "bolt-id",
            "name": "Lightning Bolt",
            "set": "lea",
            "set_name": "Limited Edition Alpha",
            "collector_number": "161",
            "rarity": "common",
            "image_uris": {"large": "https://cards.scryfall.io/normal/front/b/o/bolt.jpg"},
            "oracle_id": "abc",
        }
    ],
}

YGO_CARD = {
    "id": 46986414,
    "name": "Dark Magician",
    "type": "Spell Card",
    "card_sets": [{"set_code": "SDY", "set_name": "Starter Deck", "set_rarity": "Ultra Rare", "set_rarity_code": "UR"}],
    "card_images": [{"image_url": "https://images.ygoprodeck.com/images/cards/46986414.jpg"}],
    "card_prices": [{"tcgplayer_price": "1.00"}],
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


@pytest.mark.asyncio
async def test_import_route_requires_admin(
    api_client: AsyncClient,
    sqlite_session: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = await _make_user(sqlite_session, supabase_user_id="plain-user", role=UserRole.user)
    _patch_auth(
        monkeypatch,
        AuthUser(id=user.id, supabase_user_id=user.supabase_user_id or "plain-user", tier="free", role="user"),
    )
    r = await api_client.post("/v1/admin/sources/import/pokemon", headers={"X-Dev-User-Id": "plain-user"})
    assert r.status_code == 403


@pytest.mark.asyncio
@respx.mock
async def test_pokemon_full_import_dry_run(sqlite_session: object) -> None:
    respx.get("https://api.pokemontcg.io/v2/cards").mock(return_value=Response(200, json=POKEMON_PAGE))
    result = await start_full_catalogue_import(sqlite_session, "pokemon", dry_run=True)
    assert result.status == "success"
    assert result.inserted_count == 1
    assert result.dry_run is True


@pytest.mark.asyncio
@respx.mock
async def test_scryfall_full_import_dry_run(sqlite_session: object) -> None:
    respx.get("https://api.scryfall.com/cards/search").mock(return_value=Response(200, json=SCRYFALL_PAGE))
    result = await start_full_catalogue_import(sqlite_session, "scryfall", dry_run=True)
    assert result.status == "success"
    assert result.inserted_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_ygopro_full_import_dry_run(sqlite_session: object) -> None:
    respx.get("https://db.ygoprodeck.com/api/v7/cardinfo.php").mock(
        return_value=Response(200, json={"data": [YGO_CARD]})
    )
    result = await start_full_catalogue_import(sqlite_session, "ygopro", dry_run=True)
    assert result.status == "success"
    assert result.inserted_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_one_piece_full_import_dry_run(sqlite_session: object) -> None:
    _mock_one_piece_endpoints()
    result = await start_full_catalogue_import(sqlite_session, "one_piece", dry_run=True)
    assert result.status == "success"
    assert result.inserted_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_full_import_upserts_without_duplicates(sqlite_session: object) -> None:
    _mock_one_piece_endpoints()
    first = await start_full_catalogue_import(sqlite_session, "one_piece", dry_run=False, force=True)
    assert first.status == "queued"
    await execute_full_catalogue_import(
        uuid.UUID(first.source_run_id), "one_piece", dry_run=False, session=sqlite_session
    )
    count1 = await SourceRunsRepo(sqlite_session).count_cards_by_source("optcgapi")
    assert count1 == 1

    second = await start_full_catalogue_import(sqlite_session, "one_piece", dry_run=False, force=True)
    await execute_full_catalogue_import(
        uuid.UUID(second.source_run_id), "one_piece", dry_run=False, session=sqlite_session
    )
    count2 = await SourceRunsRepo(sqlite_session).count_cards_by_source("optcgapi")
    assert count2 == 1
    run = await SourceRunsRepo(sqlite_session).last_success("one_piece", run_type="full")
    assert run is not None
    assert run.updated_count >= 1 or run.inserted_count == 0


@pytest.mark.asyncio
@respx.mock
async def test_source_run_records_failure(sqlite_session: object) -> None:
    respx.get("https://api.pokemontcg.io/v2/cards").mock(return_value=Response(500, json={"error": "fail"}))
    queued = await start_full_catalogue_import(sqlite_session, "pokemon", dry_run=False, force=True)
    await execute_full_catalogue_import(
        uuid.UUID(queued.source_run_id), "pokemon", dry_run=False, session=sqlite_session
    )
    run_obj = await SourceRunsRepo(sqlite_session).get(uuid.UUID(queued.source_run_id))
    assert run_obj is not None
    assert run_obj.status.value == "failed"


@pytest.mark.asyncio
async def test_card_search_paginates(api_client: AsyncClient, sqlite_session: object) -> None:
    for i in range(3):
        sqlite_session.add(
            CardIdentity(
                game=Game.pokemon,
                name=f"Card {i}",
                set_code="base1",
                number=str(i),
                source="pokemontcg",
                source_card_id=f"base1-{i}",
            )
        )
    await sqlite_session.commit()
    page1 = await api_client.get("/v1/cards/search", params={"game": "pokemon", "limit": 2, "offset": 0})
    page2 = await api_client.get("/v1/cards/search", params={"game": "pokemon", "limit": 2, "offset": 2})
    assert page1.status_code == 200 and len(page1.json()) == 2
    assert page2.status_code == 200 and len(page2.json()) == 1


@pytest.mark.asyncio
@respx.mock
async def test_import_route_admin_ok(api_client: AsyncClient, admin_headers: dict[str, str]) -> None:
    respx.get("https://api.pokemontcg.io/v2/cards").mock(return_value=Response(200, json=POKEMON_PAGE))
    r = await api_client.post(
        "/v1/admin/sources/import/pokemon",
        params={"dry_run": "true"},
        headers=admin_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "success"
    assert body["inserted_count"] == 1
