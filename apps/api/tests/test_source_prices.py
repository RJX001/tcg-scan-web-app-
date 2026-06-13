import uuid
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from tcgscan_api.db.models import CardIdentity, Game, SaleEvent, SaleKind
from tcgscan_api.services.cards import get_source_prices


@pytest.mark.asyncio
async def test_source_prices_avg_and_search_urls(sqlite_session: AsyncSession) -> None:
    card_id = uuid.uuid4()
    sqlite_session.add(
        CardIdentity(
            id=card_id,
            game=Game.pokemon,
            name="Pikachu",
            set_code="base1",
            set_name="Base Set",
            number="58/102",
        )
    )
    now = datetime.now()
    for i, (source, price) in enumerate(
        [("ebay", 10.0), ("ebay", 20.0), ("tcgplayer", 15.0), ("cardmarket", 12.0)]
    ):
        sqlite_session.add(
            SaleEvent(
                id=uuid.uuid4(),
                card_id=card_id,
                source=source,
                kind=SaleKind.sold,
                sold_at=now - timedelta(days=i),
                price=Decimal(str(price)),
                currency="USD",
                price_usd=Decimal(str(price)),
            )
        )
    await sqlite_session.commit()

    out = await get_source_prices(sqlite_session, card_id, days=30)
    assert out.days == 30
    assert out.ebay_median_usd == 15.0
    assert out.tcgplayer_median_usd == 15.0
    assert out.cardmarket_median_usd == 12.0
    assert len(out.marketplaces) == 3
    ebay_tile = next(m for m in out.marketplaces if m.source == "ebay")
    assert ebay_tile.avg_usd == 15.0
    assert ebay_tile.sample_count == 2
    assert "ebay" in ebay_tile.search_url
    assert "Pikachu" in ebay_tile.search_url
