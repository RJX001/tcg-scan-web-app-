import httpx
import pytest
import respx

from tcgscan_worker.catalog.pokemon import PokemonCatalog
from tcgscan_worker.catalog.mtg import MtgCatalog
from tcgscan_worker.catalog.yugioh import YugiohCatalog


@pytest.mark.asyncio
async def test_pokemon_iter_cards_normalises() -> None:
    fixture = {
        "data": [
            {
                "id": "sv1-1",
                "name": "Sprigatito",
                "number": "1",
                "rarity": "Common",
                "set": {"id": "sv1", "name": "Scarlet & Violet"},
                "images": {"small": "https://img/s.png", "large": "https://img/l.png"},
                "hp": "70",
                "types": ["Grass"],
                "supertype": "Pokémon",
            }
        ]
    }
    with respx.MockRouter(assert_all_called=False) as route:
        route.get("https://api.pokemontcg.io/v2/cards").mock(httpx.Response(200, json=fixture))
        ingester = PokemonCatalog()
        cards = []
        async for c in ingester.iter_cards(limit=1):
            cards.append(c)
        await ingester.client.aclose()
    assert len(cards) == 1
    assert cards[0].name == "Sprigatito"
    assert cards[0].set_code == "sv1"


@pytest.mark.asyncio
async def test_mtg_iter_cards_normalises() -> None:
    fixture = {
        "data": [
            {
                "id": "ab12",
                "name": "Lightning Bolt",
                "set": "lea",
                "set_name": "Alpha",
                "collector_number": "162",
                "rarity": "common",
                "image_uris": {"large": "https://img/lea-162.png"},
                "mana_cost": "{R}",
                "type_line": "Instant",
                "colors": ["R"],
                "cmc": 1,
            }
        ],
        "has_more": False,
    }
    with respx.MockRouter(assert_all_called=False) as route:
        route.get(host="api.scryfall.com").mock(httpx.Response(200, json=fixture))
        ingester = MtgCatalog()
        cards = []
        async for c in ingester.iter_cards(limit=1):
            cards.append(c)
        await ingester.client.aclose()
    assert cards[0].set_code == "LEA"
    assert cards[0].number == "162"


@pytest.mark.asyncio
async def test_yugioh_iter_cards_normalises() -> None:
    fixture = {
        "data": [
            {
                "id": 89631139,
                "name": "Blue-Eyes White Dragon",
                "type": "Normal Monster",
                "card_sets": [
                    {
                        "set_code": "LOB-001",
                        "set_name": "Legend of Blue Eyes",
                        "set_rarity": "Ultra Rare",
                    }
                ],
                "card_images": [
                    {
                        "image_url": "https://img/bewd.png",
                        "image_url_small": "https://img/bewd_s.png",
                    }
                ],
                "atk": 3000,
                "def": 2500,
            }
        ]
    }
    with respx.MockRouter(assert_all_called=False) as route:
        route.get("https://db.ygoprodeck.com/api/v7/cardinfo.php").mock(
            httpx.Response(200, json=fixture)
        )
        ingester = YugiohCatalog()
        cards = []
        async for c in ingester.iter_cards(limit=1):
            cards.append(c)
        await ingester.client.aclose()
    assert cards[0].name == "Blue-Eyes White Dragon"
