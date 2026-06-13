import httpx
import pytest
import respx

from tcgscan_worker.catalog.sports import SportsCatalog


@pytest.mark.asyncio
async def test_sports_iter_cards_maps_game(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TCG_API_KEY", "test")
    fixture = {
        "data": [
            {
                "id": "sp-1",
                "name": "Mike Trout",
                "sport": "baseball",
                "set_code": "2011-TOPPS",
                "number": "175",
                "image": "https://img/trout.png",
            }
        ]
    }
    with respx.MockRouter(assert_all_called=False) as route:
        route.get("https://api.tcgapi.dev/v1/sports/cards").mock(httpx.Response(200, json=fixture))
        ingester = SportsCatalog()
        cards = []
        async for c in ingester.iter_cards(limit=1):
            cards.append(c)
        await ingester.client.aclose()
    assert cards[0].game == "sports_baseball"
    assert cards[0].name == "Mike Trout"
