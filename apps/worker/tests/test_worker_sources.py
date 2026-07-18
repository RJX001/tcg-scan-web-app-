import httpx
import pytest
import respx

from tcgscan_worker.sources.ebay_active import EbayActiveSource
from tcgscan_worker.sources.ebay_sold import EbaySoldSource


@pytest.mark.asyncio
async def test_ebay_active_normalises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EBAY_OAUTH_TOKEN", "test-token")
    fixture = {
        "itemSummaries": [
            {
                "itemWebUrl": "https://ebay.com/itm/1",
                "price": {"value": "12.50", "currency": "USD"},
                "condition": "Used",
            }
        ]
    }
    with respx.MockRouter(assert_all_called=False) as route:
        route.get(host="api.ebay.com").mock(httpx.Response(200, json=fixture))
        src = EbayActiveSource()
        records = []
        async for r in src.iter_records(query="charizard", limit=1):
            records.append(r)
        await src.client.aclose()
    assert records[0].source == "ebay"
    assert records[0].kind == "listing"
    assert str(records[0].price) == "12.50"


@pytest.mark.asyncio
async def test_ebay_sold_falls_back_to_browse(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EBAY_INSIGHTS_TOKEN", raising=False)
    monkeypatch.setenv("EBAY_OAUTH_TOKEN", "test-token")
    fixture = {
        "itemSummaries": [
            {
                "itemWebUrl": "https://ebay.com/itm/9",
                "price": {"value": "5.00", "currency": "USD"},
            }
        ]
    }
    with respx.MockRouter(assert_all_called=False) as route:
        route.get(host="api.ebay.com").mock(httpx.Response(200, json=fixture))
        src = EbaySoldSource()
        records = []
        async for r in src.iter_records(query="x", limit=1):
            records.append(r)
        await src.client.aclose()
    assert records[0].source == "ebay"
    assert records[0].kind == "sold"
