"""Dev seed — Pokemon sample cards + eBay comps for vertical slice demo."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from tcgscan_api.db.models import Game, SaleKind
from tcgscan_api.db.session import get_sessionmaker
from tcgscan_api.repositories.cards import CardsRepo
from tcgscan_api.repositories.sales import SalesRepo
from tcgscan_api.services.slug import card_slug

# Stable UUIDs for dev fixtures
CHARIZARD_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")
PIKACHU_ID = uuid.UUID("22222222-2222-4222-8222-222222222222")
MEWTWO_ID = uuid.UUID("33333333-3333-4333-8333-333333333333")

CARDS: list[dict[str, object]] = [
    {
        "id": CHARIZARD_ID,
        "game": Game.pokemon,
        "name": "Charizard",
        "set_code": "base1",
        "set_name": "Base Set",
        "number": "4/102",
        "rarity": "Rare Holo",
        "image_urls": {
            "front": "https://images.pokemontcg.io/base1/4_hires.png",
            "small": "https://images.pokemontcg.io/base1/4.png",
        },
        "attributes": {"hp": "120", "type": "Fire"},
        "external_ids": {"pokemontcg": "base1-4"},
    },
    {
        "id": PIKACHU_ID,
        "game": Game.pokemon,
        "name": "Pikachu",
        "set_code": "base1",
        "set_name": "Base Set",
        "number": "58/102",
        "rarity": "Common",
        "image_urls": {
            "front": "https://images.pokemontcg.io/base1/58_hires.png",
            "small": "https://images.pokemontcg.io/base1/58.png",
        },
        "attributes": {"hp": "40", "type": "Lightning"},
        "external_ids": {"pokemontcg": "base1-58"},
    },
    {
        "id": MEWTWO_ID,
        "game": Game.pokemon,
        "name": "Mewtwo",
        "set_code": "base1",
        "set_name": "Base Set",
        "number": "10/102",
        "rarity": "Rare Holo",
        "image_urls": {
            "front": "https://images.pokemontcg.io/base1/10_hires.png",
            "small": "https://images.pokemontcg.io/base1/10.png",
        },
        "attributes": {"hp": "60", "type": "Psychic"},
        "external_ids": {"pokemontcg": "base1-10"},
    },
]


def _sample_sales(card_id: uuid.UUID, base_price: Decimal) -> list[dict[str, object]]:
    now = datetime.now(timezone.utc)
    rows: list[dict[str, object]] = []
    for i in range(8):
        price = base_price + Decimal(str(i * 3.5))
        rows.append(
            {
                "card_id": card_id,
                "source": "ebay",
                "kind": SaleKind.sold,
                "sold_at": now - timedelta(days=i * 2 + 1),
                "price": price,
                "currency": "USD",
                "price_usd": price,
                "grade": "raw" if i % 3 else "PSA 9",
                "condition": "Near Mint",
                "listing_url": f"https://ebay.com/itm/seed-{card_id}-{i}",
                "raw_payload": {"seed": True},
            }
        )
    return rows


async def seed_async() -> None:
    async with get_sessionmaker()() as session:
        await CardsRepo(session).upsert_many(CARDS)
        sales = (
            _sample_sales(CHARIZARD_ID, Decimal("275.00"))
            + _sample_sales(PIKACHU_ID, Decimal("4.50"))
            + _sample_sales(MEWTWO_ID, Decimal("45.00"))
        )
        await SalesRepo(session).bulk_insert(sales)

    print("db:seed — inserted 3 Pokemon cards + sample eBay comps")
    print(f"  demo slug: {card_slug(Game.pokemon, 'base1', '4/102')}")


def main() -> None:
    asyncio.run(seed_async())


if __name__ == "__main__":
    main()
