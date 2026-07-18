from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest
import respx
import structlog
from structlog.testing import capture_logs

from tcgscan_api.db.models import Game, SaleKind
from tcgscan_api.repositories.cards import CardsRepo
from tcgscan_api.repositories.sales import SalesRepo
from tcgscan_worker.pricing import fx as fx_mod
from tcgscan_worker.pricing import ingest as ingest_mod
from tcgscan_worker.pricing.fx import to_usd
from tcgscan_worker.pricing.ingest import ingest_batch, ingest_for_card


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

        @asynccontextmanager
        async def _session():
            yield sqlite_session

        monkeypatch.setattr(ingest_mod, "card_session", _session)

        n = await ingest_for_card(card_id, sources=["ebay_sold"], limit=5)

    assert n == 1
    rows = await SalesRepo(sqlite_session).comps_for_card(card_id, days=30)
    assert len(rows) == 1
    assert rows[0].source == "ebay"
    assert rows[0].kind == SaleKind.sold
    assert rows[0].price == Decimal("9.99")


@pytest.mark.asyncio
async def test_batch_partial_failure_logs_error_and_counters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ok_id = uuid.uuid4()
    empty_id = uuid.uuid4()
    fail_id = uuid.uuid4()
    cards = [
        SimpleNamespace(id=ok_id),
        SimpleNamespace(id=empty_id),
        SimpleNamespace(id=fail_id),
    ]

    @asynccontextmanager
    async def _session():
        class _Result:
            def scalars(self) -> SimpleNamespace:
                return SimpleNamespace(all=lambda: cards)

        class _Session:
            async def execute(self, _stmt: object) -> _Result:
                return _Result()

        yield _Session()

    async def _fake_ingest(card_id: uuid.UUID, **_kwargs: object) -> int:
        if card_id == fail_id:
            raise RuntimeError("source down")
        if card_id == empty_id:
            return 0
        return 4

    monkeypatch.setattr(ingest_mod, "card_session", _session)
    monkeypatch.setattr(ingest_mod, "ingest_for_card", _fake_ingest)
    ingest_mod.log = structlog.get_logger()

    with capture_logs() as logs:
        total = await ingest_batch(card_limit=3, sources=["ebay_sold"])

    assert total == 4

    card_failed = [e for e in logs if e.get("event") == "pricing.batch.card_failed"]
    assert len(card_failed) == 1
    assert card_failed[0]["log_level"] == "warning"
    assert card_failed[0]["card_id"] == str(fail_id)
    assert "source down" in card_failed[0]["error"]

    done = [e for e in logs if e.get("event") == "pricing.batch.done"]
    assert len(done) == 1
    assert done[0]["log_level"] == "info"
    assert done[0]["cards"] == 3
    assert done[0]["rows"] == 4
    assert done[0]["failed"] == 1
    assert done[0]["empty"] == 1
    assert done[0]["success"] == 1

    partial = [e for e in logs if e.get("event") == "pricing.batch.partial_failure"]
    assert len(partial) == 1
    assert partial[0]["log_level"] == "error"
    assert partial[0]["failed"] == 1
    assert partial[0]["total"] == 3


@pytest.mark.asyncio
async def test_fx_missing_rate_logs_error_and_returns_amount(
    sqlite_session,
) -> None:
    fx_mod.log = structlog.get_logger()
    amount = Decimal("12.50")

    with capture_logs() as logs:
        result = await to_usd(sqlite_session, amount=amount, currency="JPY")

    assert result == amount
    missing = [e for e in logs if e.get("event") == "fx.missing_rate"]
    assert len(missing) == 1
    assert missing[0]["log_level"] == "error"
    assert missing[0]["currency"] == "JPY"
