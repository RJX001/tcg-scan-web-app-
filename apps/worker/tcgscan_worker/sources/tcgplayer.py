from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import datetime
from decimal import Decimal

from tcgscan_worker.http import ResilientClient
from tcgscan_worker.sources.base import PriceSource, SaleRecord, register


@register("tcgplayer")
class TcgPlayerSource(PriceSource):
    """TCGPlayer — via tcgapi.dev as primary, since direct TCGPlayer API is closed."""

    BASE_URL = "https://api.tcgapi.dev/v1"

    def _build_client(self) -> ResilientClient:
        api_key = os.getenv("TCG_API_KEY", "")
        return ResilientClient(
            base_url=self.BASE_URL,
            rate_per_sec=5.0,
            burst=10,
            headers={"Authorization": f"Bearer {api_key}"},
        )

    async def iter_records(self, *, query: str, limit: int = 100) -> AsyncIterator[SaleRecord]:
        payload = await self.client.get_json("/prices/latest", params={"q": query, "limit": limit})
        items = payload.get("data") or []
        for it in items:
            price = it.get("market_price") or it.get("low_price")
            if price is None:
                continue
            yield SaleRecord(
                source="tcgplayer",
                kind="sold",
                sold_at=datetime.now(),
                price=Decimal(str(price)),
                currency=it.get("currency", "USD"),
                price_usd=Decimal(str(price)) if it.get("currency", "USD") == "USD" else None,
                grade_company=None,
                grade=None,
                condition=it.get("condition", "NM"),
                listing_url=it.get("url"),
                raw_payload=it,
            )
