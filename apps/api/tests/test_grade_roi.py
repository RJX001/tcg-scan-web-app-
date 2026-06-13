from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from tcgscan_api.db.models import Game, SaleKind
from tcgscan_api.repositories.cards import CardsRepo
from tcgscan_api.repositories.sales import SalesRepo
from tcgscan_api.services.grade_roi import compute_verdict


@pytest.mark.asyncio
async def test_grade_verdict_recommends_grade(sqlite_session) -> None:
    card_id = uuid.UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")
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
    now = datetime.now(timezone.utc)
    await SalesRepo(sqlite_session).bulk_insert(
        [
            {
                "card_id": card_id,
                "source": "ebay",
                "kind": SaleKind.sold,
                "sold_at": now,
                "price": Decimal("200"),
                "currency": "USD",
                "price_usd": Decimal("200"),
                "grade": "raw",
            },
            {
                "card_id": card_id,
                "source": "ebay",
                "kind": SaleKind.sold,
                "sold_at": now,
                "price": Decimal("900"),
                "currency": "USD",
                "price_usd": Decimal("900"),
                "grade": "PSA 10",
            },
        ]
    )
    verdict = await compute_verdict(sqlite_session, card_id, psa_high=10)
    assert verdict is not None
    assert verdict.action == "GRADE"
    assert verdict.expected_profit_usd is not None
    assert verdict.expected_profit_usd > 0
