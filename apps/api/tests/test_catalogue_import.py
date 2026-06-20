from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
import respx
import httpx
from httpx import ASGITransport, AsyncClient, Response

from tcgscan_api.db.models import CardIdentity, Game, UserRole
from tcgscan_api.db.session import get_session
from tcgscan_api.main import app, fastapi_app
from tcgscan_api.middleware.auth import AuthUser
from tcgscan_api.repositories.source_runs import SourceRunsRepo
from tcgscan_api.services.catalogue_import import start_full_catalogue_import
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


def _pokemon_card(index: int) -> dict[str, object]:
    return {
        "id": f"base1-{index}",
        "name": f"Pokemon Card {index}",
        "number": str(index),
        "rarity": "Common",
        "set": {"id": "base1", "name": "Base", "ptcgoCode": "BS"},
        "images": {"large": f"https://images.pokemontcg.io/base1/{index}_hires.png"},
        "supertype": "Pokémon",
        "types": ["Colorless"],
    }


def _pokemon_page_payload(page: int, *, total_pages: int, page_size: int = 1) -> dict[str, object]:
    total_count = total_pages * page_size
    start = (page - 1) * page_size + 1
    data = [_pokemon_card(start + i) for i in range(page_size)]
    return {
        "data": data,
        "page": page,
        "pageSize": page_size,
        "count": len(data),
        "totalCount": total_count,
    }


def _mock_pokemon_pages(total_pages: int, *, page_size: int = 1, fail_page: int | None = None) -> None:
    def handler(request: httpx.Request) -> Response:
        page = int(request.url.params.get("page", "1"))
        if fail_page is not None and page == fail_page:
            return Response(500, json={"error": "fail"})
        return Response(200, json=_pokemon_page_payload(page, total_pages=total_pages, page_size=page_size))

    respx.get("https://api.pokemontcg.io/v2/cards").mock(side_effect=handler)

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


def _mock_one_piece_endpoints_promo_404() -> None:
    respx.get("https://optcgapi.com/api/allSetCards/").mock(return_value=Response(200, json=[OPTCG_CARD]))
    respx.get("https://optcgapi.com/api/allSTCards/").mock(return_value=Response(200, json=[]))
    respx.get("https://optcgapi.com/api/allPromoCards/").mock(return_value=Response(404, json={"detail": "Not found"}))
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
async def test_pokemon_batched_import_first_batch_returns_running(sqlite_session: object) -> None:
    _mock_pokemon_pages(2)
    first = await start_full_catalogue_import(sqlite_session, "pokemon", dry_run=False, force=True)
    assert first.status == "running"
    assert first.complete is False
    assert first.next_page_token == "2"
    assert first.inserted_count == 1

    run = await SourceRunsRepo(sqlite_session).get(uuid.UUID(first.source_run_id))
    assert run is not None
    assert run.status.value == "running"
    assert run.finished_at is None


@pytest.mark.asyncio
@respx.mock
async def test_pokemon_batched_import_completes_across_batches(sqlite_session: object) -> None:
    _mock_pokemon_pages(2)
    first = await start_full_catalogue_import(sqlite_session, "pokemon", dry_run=False, force=True)
    assert first.status == "running"
    second = await start_full_catalogue_import(
        sqlite_session,
        "pokemon",
        dry_run=False,
        force=True,
        page_token=first.next_page_token,
        source_run_id=uuid.UUID(first.source_run_id),
    )
    assert second.status == "success"
    assert second.complete is True
    assert second.inserted_count == 2

    run = await SourceRunsRepo(sqlite_session).last_success("pokemon", run_type="full")
    assert run is not None
    assert run.finished_at is not None

    count = await SourceRunsRepo(sqlite_session).count_cards_by_source("pokemontcg")
    assert count == 2


@pytest.mark.asyncio
@respx.mock
async def test_pokemon_status_endpoint_responsive_during_import(
    api_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    _mock_pokemon_pages(2)
    batch = await api_client.post(
        "/v1/admin/sources/import/pokemon",
        params={"force": "true", "batch_size": 1},
        headers=admin_headers,
    )
    assert batch.status_code == 200
    assert batch.json()["status"] == "running"

    status = await api_client.get("/v1/admin/sources/status", headers=admin_headers)
    assert status.status_code == 200
    body = status.json()
    assert "catalog_stats" in body


@pytest.mark.asyncio
@respx.mock
async def test_pokemon_duplicate_batch_updates_not_duplicates(sqlite_session: object) -> None:
    _mock_pokemon_pages(1)
    first = await start_full_catalogue_import(sqlite_session, "pokemon", dry_run=False, force=True)
    assert first.status == "success"
    assert first.inserted_count == 1

    second = await start_full_catalogue_import(sqlite_session, "pokemon", dry_run=False, force=True)
    assert second.status == "success"
    assert second.updated_count == 1
    assert second.inserted_count == 0

    count = await SourceRunsRepo(sqlite_session).count_cards_by_source("pokemontcg")
    assert count == 1


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
async def test_one_piece_full_import_succeeds_when_promo_404(sqlite_session: object) -> None:
    _mock_one_piece_endpoints_promo_404()
    result = await start_full_catalogue_import(sqlite_session, "one_piece", dry_run=False, force=True)
    assert result.status == "success"
    assert result.inserted_count == 1
    assert result.skipped_count >= 1
    assert "Promo endpoint unavailable/skipped" in result.message

    count = await SourceRunsRepo(sqlite_session).count_cards_by_source("optcgapi")
    assert count == 1

    run = await SourceRunsRepo(sqlite_session).last_success("one_piece", run_type="full")
    assert run is not None
    assert run.status.value == "success"
    assert run.run_type == "full"
    assert run.finished_at is not None
    assert run.skipped_count >= 1
    assert run.error_message is not None
    assert "promo" in run.error_message.lower()


@pytest.mark.asyncio
@respx.mock
async def test_one_piece_import_route_success_when_promo_404(
    api_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    _mock_one_piece_endpoints_promo_404()
    r = await api_client.post(
        "/v1/admin/sources/import/one-piece",
        params={"force": "true"},
        headers=admin_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "success"
    assert body["inserted_count"] == 1
    assert body["skipped_count"] >= 1
    assert "Promo endpoint unavailable/skipped" in body["message"]


@pytest.mark.asyncio
@respx.mock
async def test_full_import_runs_synchronously_and_records_success(sqlite_session: object) -> None:
    _mock_one_piece_endpoints()
    result = await start_full_catalogue_import(sqlite_session, "one_piece", dry_run=False)
    assert result.status == "success"
    assert result.inserted_count == 1
    assert result.dry_run is False

    count = await SourceRunsRepo(sqlite_session).count_cards_by_source("optcgapi")
    assert count == 1

    run = await SourceRunsRepo(sqlite_session).last_success("one_piece", run_type="full")
    assert run is not None
    assert run.status.value == "success"
    assert run.run_type == "full"
    assert run.finished_at is not None


@pytest.mark.asyncio
@respx.mock
async def test_full_import_upserts_without_duplicates(sqlite_session: object) -> None:
    _mock_one_piece_endpoints()
    first = await start_full_catalogue_import(sqlite_session, "one_piece", dry_run=False, force=True)
    assert first.status == "success"
    count1 = await SourceRunsRepo(sqlite_session).count_cards_by_source("optcgapi")
    assert count1 == 1

    second = await start_full_catalogue_import(sqlite_session, "one_piece", dry_run=False, force=True)
    assert second.status == "success"
    assert second.updated_count == 1
    count2 = await SourceRunsRepo(sqlite_session).count_cards_by_source("optcgapi")
    assert count2 == 1


@pytest.mark.asyncio
@respx.mock
async def test_source_run_records_failure(sqlite_session: object) -> None:
    respx.get("https://api.pokemontcg.io/v2/cards").mock(return_value=Response(500, json={"error": "fail"}))
    result = await start_full_catalogue_import(sqlite_session, "pokemon", dry_run=False, force=True)
    assert result.status == "failed"
    run_obj = await SourceRunsRepo(sqlite_session).get(uuid.UUID(result.source_run_id))
    assert run_obj is not None
    assert run_obj.status.value == "failed"
    assert run_obj.finished_at is not None
    assert run_obj.error_message


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
