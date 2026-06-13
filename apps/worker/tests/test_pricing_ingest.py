from __future__ import annotations

import uuid
from decimal import Decimal

import httpx
import pytest
import respx

from tcgscan_api.db.models import Game, SaleKind
from tcgscan_api.repositories.cards import CardsRepo
from tcgscan_api.repositories.sales import SalesRepo
from tcgscan_worker.pricing.ingest import ingest_for_card


@pytest.mark.asyncio
async def test_ingest_for_card_persists(sqlite_session, monkeypatch: pytest.MonkeyPatch) -> None:
    card_id = uuid.UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
    await CardsRepo(sqlite_session).upsert_many(
        [
            {
                "id": card_id,
                "game": Game.pokemon,
                "name": "Pikachu",
                "set_name": "Base Set",
                "set_code": "base1",
                "number": "58/102",
            }
        ]
    )

    fixture = {
        "itemSummaries": [
            {
                "itemWebUrl": "https://ebay.com/itm/42",
                "price": {"value": "9.99", "currency": "USD"},
            }
        ]
    }

    monkeypatch.setenv("EBAY_OAUTH_TOKEN", "test-token")

    with respx.MockRouter(assert_all_called=False) as route:
        route.get(host="api.ebay.com").mock(httpx.Response(200, json=fixture))

        # Patch card_session to use test session
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def _session():
            yield sqlite_session

        import tcgscan_worker.pricing.ingest as ingest_mod

        monkeypatch.setattr(ingest_mod, "card_session", _session)

        n = await ingest_for_card(card_id, sources=["ebay_sold"], limit=5)

    assert n == 1
    rows = await SalesRepo(sqlite_session).comps_for_card(card_id, days=30)
    assert len(rows) == 1
    assert rows[0].source == "ebay"
    assert rows[0].kind == SaleKind.sold
    assert rows[0].price == Decimal("9.99")
