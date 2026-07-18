from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
import respx
from httpx import ASGITransport, AsyncClient, Response

from tcgscan_api.db.models import UserRole
from tcgscan_api.db.session import get_session
from tcgscan_api.main import app, fastapi_app
from tcgscan_api.middleware.auth import AuthUser
from tcgscan_api.sources.one_piece import OnePieceClient, normalize_card as normalize_one_piece
from tcgscan_api.sources.ygoprodeck import YgoProDeckClient, normalize_card as normalize_ygo
from tests.test_admin import _make_user, _patch_auth

YGOPRO_SAMPLE = {
    "data": [
        {
            "id": 46986414,
            "name": "Dark Magician",
            "type": "Normal Monster",
            "desc": "The ultimate wizard.",
            "race": "Spellcaster",
            "attribute": "DARK",
            "archetype": "Dark Magician",
            "level": 7,
            "atk": 2500,
            "def": 2100,
            "card_sets": [
                {
                    "set_name": "Legend of Blue Eyes White Dragon",
                    "set_code": "LOB-EN005",
                    "set_rarity": "Ultra Rare",
                }
            ],
            "card_images": [
                {"image_url": "https://images.ygoprodeck.com/images/cards/46986414.jpg"}
            ],
            "card_prices": [{"tcgplayer_price": "0.27"}],
        }
    ]
}

OPTCG_SETS = [{"set_name": "Romance Dawn", "set_id": "OP-01"}]
OPTCG_CARD = [
    {
        "card_name": "Perona",
        "set_name": "Romance Dawn",
        "set_id": "OP-01",
        "rarity": "UC",
        "card_set_id": "OP01-077",
        "card_color": "Blue",
        "card_type": "Character",
        "card_cost": "1",
        "card_power": "2000",
        "counter_amount": 1000,
        "attribute": "Special",
        "sub_types": "Thriller Bark Pirates",
        "card_text": "[On Play] Look at 5 cards.",
        "card_image": "https://optcgapi.com/media/static/Card_Images/OP01-077.jpg",
    }
]


def _mock_one_piece_endpoints_promo_404() -> None:
    respx.get("https://optcgapi.com/api/allSetCards/").mock(
        return_value=Response(200, json=[OPTCG_CARD[0]])
    )
    respx.get("https://optcgapi.com/api/allSTCards/").mock(return_value=Response(200, json=[]))
    respx.get("https://optcgapi.com/api/allPromoCards/").mock(
        return_value=Response(404, json={"detail": "Not found"})
    )
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
        AuthUser(
            id=user.id,
            supabase_user_id=user.supabase_user_id or "admin-user",
            tier="free",
            role="admin",
        ),
    )
    return {"X-Dev-User-Id": "admin-user"}


def test_ygopro_normalize_maps_fields() -> None:
    card = normalize_ygo(YGOPRO_SAMPLE["data"][0])
    assert card["game"] == "yugioh"
    assert card["source"] == "ygoprodeck"
    assert card["source_card_id"] == "46986414"
    assert card["name"] == "Dark Magician"
    assert card["metadata"]["card_prices"][0]["tcgplayer_price"] == "0.27"


def test_one_piece_normalize_maps_fields() -> None:
    card = normalize_one_piece(OPTCG_CARD[0])
    assert card["game"] == "one_piece"
    assert card["source"] == "optcgapi"
    assert card["source_card_id"] == "OP01-077"
    assert card["name"] == "Perona"
    assert card["colour"] == "Blue"


@pytest.mark.asyncio
@respx.mock
async def test_ygopro_diagnostic_success(
    admin_headers: dict[str, str], api_client: AsyncClient
) -> None:
    respx.get("https://db.ygoprodeck.com/api/v7/cardinfo.php").mock(
        return_value=Response(200, json=YGOPRO_SAMPLE)
    )
    r = await api_client.get("/v1/admin/sources/test/ygopro", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "success"
    assert body["provider"] == "ygoprodeck"
    assert body["sample_card_name"] == "Dark Magician"
    assert body["sample_card_id"] == "46986414"
    assert "data" not in body


@pytest.mark.asyncio
@respx.mock
async def test_one_piece_diagnostic_success(
    admin_headers: dict[str, str], api_client: AsyncClient
) -> None:
    respx.get("https://optcgapi.com/api/allSets/").mock(return_value=Response(200, json=OPTCG_SETS))
    respx.get("https://optcgapi.com/api/sets/card/OP01-077/").mock(
        return_value=Response(200, json=OPTCG_CARD)
    )
    r = await api_client.get("/v1/admin/sources/test/one-piece", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "success"
    assert body["provider"] == "optcgapi"
    assert body["sample_card_name"] == "Perona"
    assert body["set_count"] == 1


@pytest.mark.asyncio
@respx.mock
async def test_dragon_ball_fusion_world_not_implemented(
    admin_headers: dict[str, str],
    api_client: AsyncClient,
) -> None:
    respx.get(url__regex=r".*dbs-cardgame\.com.*").mock(
        return_value=Response(
            200,
            text="<html><title>Fusion World</title></html>",
            headers={"content-type": "text/html"},
        )
    )
    r = await api_client.get(
        "/v1/admin/sources/test/dragon-ball-fusion-world", headers=admin_headers
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in {"not_implemented", "partial", "failed"}
    assert body["provider"] == "bandai_fusion_world"
    assert "JSON adapter" in body["message"] or "unreachable" in body["message"].lower()


@pytest.mark.asyncio
@respx.mock
async def test_dragon_ball_masters_not_implemented(
    admin_headers: dict[str, str],
    api_client: AsyncClient,
) -> None:
    respx.get(url__regex=r".*dbs-cardgame\.com.*").mock(
        return_value=Response(
            200, text="<html><title>Masters</title></html>", headers={"content-type": "text/html"}
        )
    )
    r = await api_client.get("/v1/admin/sources/test/dragon-ball-masters", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in {"not_implemented", "partial", "failed"}
    assert body["provider"] == "bandai_masters"


@pytest.mark.asyncio
@respx.mock
async def test_ygopro_failure_does_not_crash_status(
    admin_headers: dict[str, str],
    api_client: AsyncClient,
) -> None:
    respx.get("https://db.ygoprodeck.com/api/v7/cardinfo.php").mock(return_value=Response(500))
    status_r = await api_client.get("/v1/admin/sources/status", headers=admin_headers)
    assert status_r.status_code == 200
    test_r = await api_client.get("/v1/admin/sources/test/ygopro", headers=admin_headers)
    assert test_r.status_code == 200
    assert test_r.json()["status"] == "failed"


@pytest.mark.asyncio
async def test_sources_test_requires_admin(
    api_client: AsyncClient, sqlite_session: object, monkeypatch: pytest.MonkeyPatch
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
    r = await api_client.get(
        "/v1/admin/sources/test/ygopro", headers={"X-Dev-User-Id": "plain-user"}
    )
    assert r.status_code == 403


@pytest.mark.asyncio
@respx.mock
async def test_ygopro_client_search_mocked() -> None:
    respx.get("https://db.ygoprodeck.com/api/v7/cardinfo.php").mock(
        return_value=Response(200, json=YGOPRO_SAMPLE)
    )
    client = YgoProDeckClient()
    try:
        cards = await client.search_card("Dark Magician")
        assert len(cards) == 1
        assert cards[0]["name"] == "Dark Magician"
    finally:
        await client.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_one_piece_iter_all_cards_skips_promo_404() -> None:
    _mock_one_piece_endpoints_promo_404()
    client = OnePieceClient()
    try:
        result = await client.iter_all_cards()
        assert len(result.cards) == 1
        assert result.cards[0]["source_card_id"] == "OP01-077"
        assert result.optional_skip_count == 1
        assert any("promo" in label.lower() for label in result.skipped_optional_endpoints)
    finally:
        await client.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_one_piece_client_sets_mocked() -> None:
    respx.get("https://optcgapi.com/api/allSets/").mock(return_value=Response(200, json=OPTCG_SETS))
    client = OnePieceClient()
    try:
        sets = await client.get_all_sets()
        assert len(sets) == 1
        assert sets[0]["set_id"] == "OP-01"
    finally:
        await client.aclose()
