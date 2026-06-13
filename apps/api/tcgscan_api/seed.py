"""Dev seed — multi-TCG sample cards + marketplace comps for scan/search demo."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from tcgscan_api.db.models import Game, SaleKind, UserRole, UserTier
from tcgscan_api.db.session import get_sessionmaker
from tcgscan_api.repositories.cards import CardsRepo
from tcgscan_api.repositories.fx import FxRepo
from tcgscan_api.repositories.market import PopulationRepo
from tcgscan_api.repositories.sales import SalesRepo
from tcgscan_api.repositories.users import UsersRepo
from tcgscan_api.services.slug import card_slug

MTG_BOLT_ID = uuid.UUID("88111111-1111-4111-8111-111111111111")
YGO_DARK_MAGICIAN_ID = uuid.UUID("88222222-2222-4222-8222-222222222222")
LORCANA_MICKEY_ID = uuid.UUID("88333333-3333-4333-8333-333333333333")
ONE_PIECE_LUFFY_ID = uuid.UUID("88444444-4444-4444-8444-444444444444")

# Stable UUIDs for dev fixtures
CHARIZARD_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")
BLASTOISE_ID = uuid.UUID("44444444-4444-4444-8444-444444444444")
VENUSAUR_ID = uuid.UUID("55555555-5555-4555-8555-555555555555")
PIKACHU_ID = uuid.UUID("22222222-2222-4222-8222-222222222222")
MEWTWO_ID = uuid.UUID("33333333-3333-4333-8333-333333333333")
ALAKAZAM_ID = uuid.UUID("66666666-6666-4666-8666-666666666666")
GYARADOS_ID = uuid.UUID("77777777-7777-4777-8777-777777777777")

# Previous-month price multiplier per card — drives the 1M % change on /ladder.
# < 1.0 means the card was cheaper last month (it gained), > 1.0 means it dropped.
PREV_MONTH_MULTIPLIER: dict[uuid.UUID, Decimal] = {
    CHARIZARD_ID: Decimal("0.78"),  # big gainer
    BLASTOISE_ID: Decimal("0.92"),
    VENUSAUR_ID: Decimal("1.05"),
    PIKACHU_ID: Decimal("0.85"),
    MEWTWO_ID: Decimal("1.18"),  # big loser
    ALAKAZAM_ID: Decimal("0.97"),
    GYARADOS_ID: Decimal("1.02"),
    MTG_BOLT_ID: Decimal("0.95"),
    YGO_DARK_MAGICIAN_ID: Decimal("0.88"),
    LORCANA_MICKEY_ID: Decimal("1.08"),
    ONE_PIECE_LUFFY_ID: Decimal("0.91"),
}

# (card_id, ebay_base_usd, tcgplayer_usd, cardmarket_usd)
PRICES: dict[uuid.UUID, tuple[Decimal, Decimal, Decimal]] = {
    CHARIZARD_ID: (Decimal("275.00"), Decimal("289.00"), Decimal("248.00")),
    BLASTOISE_ID: (Decimal("145.00"), Decimal("152.00"), Decimal("138.00")),
    VENUSAUR_ID: (Decimal("125.00"), Decimal("131.00"), Decimal("119.00")),
    PIKACHU_ID: (Decimal("4.50"), Decimal("5.25"), Decimal("4.80")),
    MEWTWO_ID: (Decimal("45.00"), Decimal("48.00"), Decimal("42.00")),
    ALAKAZAM_ID: (Decimal("38.00"), Decimal("41.00"), Decimal("36.00")),
    GYARADOS_ID: (Decimal("52.00"), Decimal("55.00"), Decimal("49.00")),
    MTG_BOLT_ID: (Decimal("3.50"), Decimal("4.25"), Decimal("3.80")),
    YGO_DARK_MAGICIAN_ID: (Decimal("28.00"), Decimal("32.00"), Decimal("26.50")),
    LORCANA_MICKEY_ID: (Decimal("12.00"), Decimal("14.50"), Decimal("11.00")),
    ONE_PIECE_LUFFY_ID: (Decimal("18.00"), Decimal("22.00"), Decimal("16.50")),
}


def _pokemon_image(set_code: str, card_num: int) -> dict[str, str]:
    base = f"https://images.pokemontcg.io/{set_code}/{card_num}"
    return {"front": f"{base}_hires.png", "small": f"{base}.png"}


CARDS: list[dict[str, object]] = [
    {
        "id": CHARIZARD_ID,
        "game": Game.pokemon,
        "name": "Charizard",
        "set_code": "base1",
        "set_name": "Base Set",
        "number": "4/102",
        "rarity": "Rare Holo",
        "image_urls": _pokemon_image("base1", 4),
        "attributes": {"hp": "120", "type": "Fire"},
        "external_ids": {"pokemontcg": "base1-4"},
    },
    {
        "id": BLASTOISE_ID,
        "game": Game.pokemon,
        "name": "Blastoise",
        "set_code": "base1",
        "set_name": "Base Set",
        "number": "2/102",
        "rarity": "Rare Holo",
        "image_urls": _pokemon_image("base1", 2),
        "attributes": {"hp": "100", "type": "Water"},
        "external_ids": {"pokemontcg": "base1-2"},
    },
    {
        "id": VENUSAUR_ID,
        "game": Game.pokemon,
        "name": "Venusaur",
        "set_code": "base1",
        "set_name": "Base Set",
        "number": "15/102",
        "rarity": "Rare Holo",
        "image_urls": _pokemon_image("base1", 15),
        "attributes": {"hp": "100", "type": "Grass"},
        "external_ids": {"pokemontcg": "base1-15"},
    },
    {
        "id": PIKACHU_ID,
        "game": Game.pokemon,
        "name": "Pikachu",
        "set_code": "base1",
        "set_name": "Base Set",
        "number": "58/102",
        "rarity": "Common",
        "image_urls": _pokemon_image("base1", 58),
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
        "image_urls": _pokemon_image("base1", 10),
        "attributes": {"hp": "60", "type": "Psychic"},
        "external_ids": {"pokemontcg": "base1-10"},
    },
    {
        "id": ALAKAZAM_ID,
        "game": Game.pokemon,
        "name": "Alakazam",
        "set_code": "base1",
        "set_name": "Base Set",
        "number": "1/102",
        "rarity": "Rare Holo",
        "image_urls": _pokemon_image("base1", 1),
        "attributes": {"hp": "80", "type": "Psychic"},
        "external_ids": {"pokemontcg": "base1-1"},
    },
    {
        "id": GYARADOS_ID,
        "game": Game.pokemon,
        "name": "Gyarados",
        "set_code": "base1",
        "set_name": "Base Set",
        "number": "6/102",
        "rarity": "Rare Holo",
        "image_urls": _pokemon_image("base1", 6),
        "attributes": {"hp": "100", "type": "Water"},
        "external_ids": {"pokemontcg": "base1-6"},
    },
    {
        "id": MTG_BOLT_ID,
        "game": Game.mtg,
        "name": "Lightning Bolt",
        "set_code": "m10",
        "set_name": "Magic 2010",
        "number": "146",
        "rarity": "common",
        "image_urls": {
            "normal": "https://cards.scryfall.io/normal/front/0/4/0431e2e3-ebf4-44e5-931b-0c416e76a1b8.jpg",
            "large": "https://cards.scryfall.io/large/front/0/4/0431e2e3-ebf4-44e5-931b-0c416e76a1b8.jpg",
        },
        "attributes": {"type_line": "Instant", "mana_cost": "{R}"},
        "external_ids": {"scryfall_id": "0431e2e3-ebf4-44e5-931b-0c416e76a1b8"},
    },
    {
        "id": YGO_DARK_MAGICIAN_ID,
        "game": Game.yugioh,
        "name": "Dark Magician",
        "set_code": "sdy",
        "set_name": "Starter Deck: Yugi",
        "number": "006",
        "rarity": "Ultra Rare",
        "image_urls": {
            "small": "https://images.ygoprodeck.com/images/cards_small/46986414.jpg",
            "large": "https://images.ygoprodeck.com/images/cards/46986414.jpg",
        },
        "attributes": {"type": "Spellcaster", "level": 7},
        "external_ids": {"ygoprodeck_id": "46986414"},
    },
    {
        "id": LORCANA_MICKEY_ID,
        "game": Game.lorcana,
        "name": "Mickey Mouse - Brave Little Tailor",
        "set_code": "tfc",
        "set_name": "The First Chapter",
        "number": "001",
        "rarity": "Legendary",
        "image_urls": {
            "large": "https://cards.lorcast.io/card/digital/large/TFC/001/en",
        },
        "attributes": {"cost": 8, "type": "Character"},
        "external_ids": {"lorcast_id": "TFC-001"},
    },
    {
        "id": ONE_PIECE_LUFFY_ID,
        "game": Game.one_piece,
        "name": "Monkey.D.Luffy",
        "set_code": "op01",
        "set_name": "Romance Dawn",
        "number": "001",
        "rarity": "Leader",
        "image_urls": {
            "large": "https://optcgapi.com/images/cards/OP01-001.png",
        },
        "attributes": {"color": "Red", "type": "Leader"},
        "external_ids": {"optcgapi_id": "OP01-001"},
    },
]

DEMO_SLUGS = [
    card_slug(Game.pokemon, "base1", "4/102"),
    card_slug(Game.pokemon, "base1", "58/102"),
    card_slug(Game.mtg, "m10", "146"),
    card_slug(Game.yugioh, "sdy", "006"),
    card_slug(Game.lorcana, "tfc", "001"),
    card_slug(Game.one_piece, "op01", "001"),
]


SOLD_GRADES = ("raw", "PSA 9", "BGS 9.5", "CGC 9", "ACE 10")
LISTING_GRADES = ("raw", "PSA 9", "BGS 9.5", "CGC 9", "ACE 10")

# PSA population per card: (PSA 10, PSA 9, PSA 8) — dev approximations
POPULATIONS: dict[uuid.UUID, tuple[int, int, int]] = {
    CHARIZARD_ID: (4274, 14688, 11237),
    BLASTOISE_ID: (2511, 8954, 6120),
    VENUSAUR_ID: (2103, 7421, 5318),
    PIKACHU_ID: (1530, 3905, 2210),
    MEWTWO_ID: (1893, 6534, 4002),
    ALAKAZAM_ID: (1278, 5210, 3540),
    GYARADOS_ID: (1654, 5879, 3877),
    MTG_BOLT_ID: (890, 4200, 3100),
    YGO_DARK_MAGICIAN_ID: (2100, 9800, 7200),
    LORCANA_MICKEY_ID: (540, 2100, 1500),
    ONE_PIECE_LUFFY_ID: (1200, 4500, 3200),
}


def _sample_population(card_id: uuid.UUID) -> list[dict[str, object]]:
    pops = POPULATIONS.get(card_id)
    if pops is None:
        return []
    now = datetime.now(timezone.utc)
    return [
        {
            "card_id": card_id,
            "grade_company": "PSA",
            "grade": grade,
            "pop_count": count,
            "as_of": now,
        }
        for grade, count in zip(("10", "9", "8"), pops)
    ]


def _sample_sales(card_id: uuid.UUID, base_price: Decimal) -> list[dict[str, object]]:
    now = datetime.now(timezone.utc)
    rows: list[dict[str, object]] = []
    prices = PRICES.get(card_id, (base_price, base_price, base_price))
    ebay_base, tcg_base, cm_base = prices

    for i in range(8):
        price = ebay_base + Decimal(str(i * 3.5))
        grade = SOLD_GRADES[i % len(SOLD_GRADES)]
        rows.append(
            {
                "card_id": card_id,
                "source": "ebay",
                "kind": SaleKind.sold,
                "sold_at": now - timedelta(days=i * 2 + 1),
                "price": price,
                "currency": "USD",
                "price_usd": price,
                "grade": grade,
                "condition": "Near Mint",
                "listing_url": f"https://ebay.com/itm/seed-{card_id}-{i}",
                "raw_payload": {"seed": True},
            }
        )

    for i in range(3):
        price = tcg_base + Decimal(str(i * 2))
        grade = SOLD_GRADES[(i + 1) % len(SOLD_GRADES)]
        rows.append(
            {
                "card_id": card_id,
                "source": "tcgplayer",
                "kind": SaleKind.sold,
                "sold_at": now - timedelta(days=i * 3 + 2),
                "price": price,
                "currency": "USD",
                "price_usd": price,
                "grade": grade,
                "condition": "Near Mint",
                "listing_url": f"https://tcgplayer.com/seed-{card_id}-{i}",
                "raw_payload": {"seed": True},
            }
        )

    for i in range(2):
        price = cm_base + Decimal(str(i * 2.5))
        grade = SOLD_GRADES[(i + 2) % len(SOLD_GRADES)]
        rows.append(
            {
                "card_id": card_id,
                "source": "cardmarket",
                "kind": SaleKind.sold,
                "sold_at": now - timedelta(days=i * 4 + 1),
                "price": price,
                "currency": "EUR",
                "price_usd": price,
                "grade": grade,
                "condition": "Near Mint",
                "listing_url": f"https://www.cardmarket.com/en/Pokemon/seed-{card_id}-{i}",
                "raw_payload": {"seed": True},
            }
        )

    for i in range(2):
        price = ebay_base * Decimal("0.82") + Decimal(str(i * 2))
        grade = SOLD_GRADES[i % len(SOLD_GRADES)]
        rows.append(
            {
                "card_id": card_id,
                "source": "ebay",
                "kind": SaleKind.sold,
                "sold_at": now - timedelta(days=i * 5 + 3),
                "price": price,
                "currency": "GBP",
                "price_usd": price * Decimal("1.27"),
                "grade": grade,
                "condition": "Near Mint",
                "listing_url": f"https://www.ebay.co.uk/itm/seed-{card_id}-uk-{i}",
                "raw_payload": {"seed": True, "marketplace_id": "EBAY_GB"},
            }
        )

    # Previous-month comps (days 32-53) so /ladder has a baseline for 1M % change
    prev_mult = PREV_MONTH_MULTIPLIER.get(card_id, Decimal("1.00"))
    for i in range(6):
        price = (ebay_base * prev_mult + Decimal(str(i * 2))).quantize(Decimal("0.01"))
        grade = SOLD_GRADES[i % len(SOLD_GRADES)]
        rows.append(
            {
                "card_id": card_id,
                "source": "ebay",
                "kind": SaleKind.sold,
                "sold_at": now - timedelta(days=32 + i * 4),
                "price": price,
                "currency": "USD",
                "price_usd": price,
                "grade": grade,
                "condition": "Near Mint",
                "listing_url": f"https://ebay.com/itm/seed-{card_id}-prev-{i}",
                "raw_payload": {"seed": True},
            }
        )
    return rows


def _sample_listings(card_id: uuid.UUID, base_price: Decimal) -> list[dict[str, object]]:
    now = datetime.now(timezone.utc)
    rows: list[dict[str, object]] = []
    regional = (
        ("us", "ebay", "USD", f"https://www.ebay.com/itm/listing-{card_id}-us"),
        ("us", "tcgplayer", "USD", f"https://www.tcgplayer.com/product/seed-{card_id}"),
        ("uk", "ebay", "GBP", f"https://www.ebay.co.uk/itm/listing-{card_id}-uk"),
        ("eu", "cardmarket", "EUR", f"https://www.cardmarket.com/en/Pokemon/listing-{card_id}-eu"),
    )
    for i, grade in enumerate(LISTING_GRADES):
        _region, source, currency, url = regional[i % len(regional)]
        multiplier = Decimal("0.92") + Decimal(str(i)) * Decimal("0.04")
        price = base_price * multiplier
        rows.append(
            {
                "card_id": card_id,
                "source": source,
                "kind": SaleKind.listing,
                "sold_at": now,
                "price": price,
                "currency": currency,
                "price_usd": price,
                "grade": grade,
                "listing_url": url,
                "raw_payload": {"seed": True, "active": True},
            }
        )
    return rows


async def seed_async() -> None:
    card_ids = [c["id"] for c in CARDS]
    assert all(isinstance(cid, uuid.UUID) for cid in card_ids)

    async with get_sessionmaker()() as session:
        await CardsRepo(session).upsert_many(CARDS)

        sales: list[dict[str, object]] = []
        listings: list[dict[str, object]] = []
        for card in CARDS:
            cid = card["id"]
            assert isinstance(cid, uuid.UUID)
            ebay_base = PRICES.get(cid, (Decimal("10.00"), Decimal("10.00"), Decimal("10.00")))[0]
            sales.extend(_sample_sales(cid, ebay_base))
            if cid in (
                CHARIZARD_ID,
                BLASTOISE_ID,
                PIKACHU_ID,
                MEWTWO_ID,
                MTG_BOLT_ID,
                YGO_DARK_MAGICIAN_ID,
                LORCANA_MICKEY_ID,
                ONE_PIECE_LUFFY_ID,
            ):
                listings.extend(_sample_listings(cid, ebay_base))

        await SalesRepo(session).bulk_insert(sales)
        await SalesRepo(session).bulk_insert(listings)

        pops: list[dict[str, object]] = []
        for card in CARDS:
            cid = card["id"]
            assert isinstance(cid, uuid.UUID)
            pops.extend(_sample_population(cid))
        await PopulationRepo(session).upsert_many(pops)

        now = datetime.now(timezone.utc)
        for cid in card_ids:
            assert isinstance(cid, uuid.UUID)
            for d in range(60):
                day = now - timedelta(days=d)
                await SalesRepo(session).rollup_day(cid, day)

        # Demo FX rates (value of 1 unit in USD) — production rates come from
        # the worker's ECB/frankfurter source on a daily schedule.
        await FxRepo(session).upsert_many(
            day=now.replace(hour=0, minute=0, second=0, microsecond=0),
            rates_to_usd={
                "USD": 1.0,
                "GBP": 1.27,
                "EUR": 1.08,
                "JPY": 0.0066,
                "CAD": 0.73,
                "AUD": 0.66,
                "CHF": 1.11,
            },
        )

        dev_user = await UsersRepo(session).get_or_create(
            clerk_id="dev-user", email="dev@localhost"
        )
        if dev_user.tier != UserTier.pro:
            await UsersRepo(session).set_tier(dev_user.id, UserTier.pro)
        if dev_user.role != UserRole.owner:
            await UsersRepo(session).set_role(dev_user.id, UserRole.owner)

    print(f"db:seed — inserted {len(CARDS)} catalog cards (Pokemon, MTG, Yu-Gi-Oh!, Lorcana, One Piece)")
    print("  dev-user tier: pro, role: owner (admin dashboard enabled)")
    print("  demo slugs:")
    for slug in DEMO_SLUGS:
        print(f"    /card/{slug}")


def main() -> None:
    asyncio.run(seed_async())


if __name__ == "__main__":
    main()
