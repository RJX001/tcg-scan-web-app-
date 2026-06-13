from __future__ import annotations

import uuid

import pytest

from tcgscan_api.db.models import Game
from tcgscan_api.repositories.cards import CardsRepo
from tcgscan_api.services.slug import card_slug, parse_card_slug


@pytest.mark.asyncio
async def test_card_slug_roundtrip() -> None:
    slug = card_slug(Game.pokemon, "base1", "4/102")
    assert slug == "pokemon-base1-4-102"
    game, set_code, number = parse_card_slug(slug)
    assert game == "pokemon"
    assert set_code == "base1"
    assert number == "4/102"


@pytest.mark.asyncio
async def test_get_by_slug(sqlite_session) -> None:
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
