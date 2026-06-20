from __future__ import annotations

import uuid

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from tcgscan_api.db.models import CardIdentity, Game
from tcgscan_api.db.session import get_session
from tcgscan_api.main import app, fastapi_app
from tcgscan_api.repositories.cards import CardsRepo
from tcgscan_api.services.slug import (
    card_slug,
    card_slug_from_identity,
    card_slug_from_source,
    match_game_prefix,
    parse_card_slug,
)


@pytest.mark.asyncio
async def test_card_slug_roundtrip() -> None:
    slug = card_slug(Game.pokemon, "base1", "4/102")
    assert slug == "pokemon-base1-4-102"
    game, set_code, number = parse_card_slug(slug)
    assert game == "pokemon"
    assert set_code == "base1"
    assert number == "4/102"


def test_one_piece_slug_format() -> None:
    slug = card_slug(Game.one_piece, "ST-08", "ST08-004")
    assert slug == "one_piece-st-08-st08-004"
    assert match_game_prefix(slug) == Game.one_piece


def test_match_game_prefix_prefers_longest_game() -> None:
    slug = "dragon_ball_fusion_world-set1-001"
    assert match_game_prefix(slug) == Game.dragon_ball_fusion_world


def test_source_slug_format() -> None:
    slug = card_slug_from_source(Game.one_piece, "optcgapi", "ST08-004")
    assert slug == "one_piece-optcgapi-st08-004"


@pytest.mark.asyncio
async def test_get_by_slug(sqlite_session: object) -> None:
    card_id = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    await CardsRepo(sqlite_session).upsert_many(
        [
            {
                "id": card_id,
                "game": Game.pokemon,
                "name": "Charizard",
                "set_code": "base1",
                "number": "4/102",
            }
        ]
    )
    card = await CardsRepo(sqlite_session).get_by_slug("pokemon-base1-4-102")
    assert card is not None
    assert card.name == "Charizard"


@pytest.mark.asyncio
async def test_get_by_slug_one_piece_hyphenated_set(sqlite_session: object) -> None:
    card_id = uuid.UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
    card = CardIdentity(
        id=card_id,
        game=Game.one_piece,
        name="Starter Card",
        set_code="ST-08",
        set_name="Starter Deck 08",
        number="ST08-004",
        source="optcgapi",
        source_card_id="ST08-004",
    )
    sqlite_session.add(card)
    await sqlite_session.commit()

    assert card_slug_from_identity(card) == "one_piece-st-08-st08-004"

    found = await CardsRepo(sqlite_session).get_by_slug("one_piece-st-08-st08-004")
    assert found is not None
    assert found.name == "Starter Card"
    assert found.source_card_id == "ST08-004"


@pytest.mark.asyncio
async def test_by_slug_route_returns_one_piece_card(sqlite_session: object) -> None:
    card_id = uuid.UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")
    sqlite_session.add(
        CardIdentity(
            id=card_id,
            game=Game.one_piece,
            name="Perona",
            set_code="OP-01",
            set_name="Romance Dawn",
            number="OP01-077",
            source="optcgapi",
            source_card_id="OP01-077",
            image_urls={"large": "https://example.com/op01-077.jpg"},
        )
    )
    await sqlite_session.commit()

    async def override_session() -> AsyncIterator[object]:
        yield sqlite_session

    fastapi_app.dependency_overrides[get_session] = override_session
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get("/v1/cards/by-slug/one_piece-op-01-op01-077")
            assert r.status_code == 200
            body = r.json()
            assert body["name"] == "Perona"
            assert body["slug"] == "one_piece-op-01-op01-077"
            assert body["price_status"] == "pending"
            assert body["image_url"] == "https://example.com/op01-077.jpg"

            legacy = await client.get("/v1/cards/slug/one_piece-op-01-op01-077")
            assert legacy.status_code == 200
            assert legacy.json()["id"] == body["id"]

            missing = await client.get("/v1/cards/by-slug/does-not-exist")
            assert missing.status_code == 404
    finally:
        fastapi_app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_search_returns_resolvable_slug(sqlite_session: object) -> None:
    sqlite_session.add(
        CardIdentity(
            game=Game.one_piece,
            name="Perona",
            set_code="OP-01",
            number="OP01-077",
            source="optcgapi",
            source_card_id="OP01-077",
        )
    )
    await sqlite_session.commit()

    async def override_session() -> AsyncIterator[object]:
        yield sqlite_session

    fastapi_app.dependency_overrides[get_session] = override_session
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            search = await client.get("/v1/cards/search", params={"q": "Perona"})
            assert search.status_code == 200
            body = search.json()
            assert len(body) == 1
            slug = body[0]["slug"]
            assert slug == "one_piece-op-01-op01-077"

            detail = await client.get(f"/v1/cards/by-slug/{slug}")
            assert detail.status_code == 200
            assert detail.json()["name"] == "Perona"
    finally:
        fastapi_app.dependency_overrides.clear()
