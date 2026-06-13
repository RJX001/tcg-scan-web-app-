from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from tcgscan_api.db.models import Game, SaleKind
from tcgscan_api.repositories.cards import CardsRepo
from tcgscan_api.repositories.sales import SalesRepo


@pytest.mark.asyncio
async def test_cards_repo_upsert_and_get(sqlite_session: AsyncSession) -> None:
    repo = CardsRepo(sqlite_session)
    n = await repo.upsert_many(
        [
            {
                "game": Game.pokemon,
                "name": "Charizard",
                "set_code": "base",
                "set_name": "Base Set",
                "number": "4",
                "rarity": "Holo Rare",
                "image_urls": {"large": "https://img/c.png"},
                "external_ids": {"pokemontcg_io": "base-4"},
                "attributes": {"hp": "120"},
                "variants": {},
            }
        ]
    )
    assert n == 1
    fetched = await repo.get_by_external(Game.pokemon, "base", "4")
    assert fetched is not None
    assert fetched.name == "Charizard"


@pytest.mark.asyncio
async def test_sales_repo_inserts_and_lists_comps(sqlite_session: AsyncSession) -> None:
    cards = CardsRepo(sqlite_session)
    await cards.upsert_many(
        [{"game": Game.pokemon, "name": "Pikachu", "set_code": "base", "number": "58"}]
    )
    card = await cards.get_by_external(Game.pokemon, "base", "58")
    assert card is not None

    sales = SalesRepo(sqlite_session)
    now = datetime.now()
    written = await sales.bulk_insert(
        [
            {
                "card_id": card.id,
                "source": "ebay",
                "kind": SaleKind.sold,
                "sold_at": now,
                "price": Decimal("25.00"),
                "currency": "USD",
                "price_usd": Decimal("25.00"),
                "listing_url": "https://ebay.com/itm/1",
                "raw_payload": {},
            }
        ]
    )
    assert written == 1
    comps = await sales.comps_for_card(card.id, days=7)
    assert len(comps) == 1
    assert comps[0].price == Decimal("25.00")


@pytest.mark.asyncio
async def test_card_lookup_missing_returns_none(sqlite_session: AsyncSession) -> None:
    repo = CardsRepo(sqlite_session)
    assert await repo.get(uuid.uuid4()) is None
    assert await repo.get_by_external(Game.mtg, "lea", "162") is None
