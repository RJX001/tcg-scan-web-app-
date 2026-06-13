from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import datetime
from decimal import Decimal

from tcgscan_worker.http import ResilientClient
from tcgscan_worker.sources.base import PriceSource, SaleRecord, register


@register("cardmarket")
class CardmarketSource(PriceSource):
    """Cardmarket — via Apify actor dataset poll."""

    BASE_URL = "https://api.apify.com/v2"

    def _build_client(self) -> ResilientClient:
        token = os.getenv("APIFY_TOKEN", "")
        return ResilientClient(
            base_url=self.BASE_URL,
            rate_per_sec=1.0,
            burst=2,
            headers={"Authorization": f"Bearer {token}"},
        )

    def _dataset_path(self) -> str:
        dataset_id = os.getenv("APIFY_CARDMARKET_DATASET_ID", "cardmarket-trend")
        return f"/datasets/{dataset_id}/items"

    async def iter_records(self, *, query: str, limit: int = 100) -> AsyncIterator[SaleRecord]:
        payload = await self.client.get_json(
            self._dataset_path(),
            params={"limit": limit, "clean": "true", "search": query},
        )
        items = (
            payload
            if isinstance(payload, list)
            else payload.get("data") or payload.get("items") or []
        )
        for it in items:
            if not isinstance(it, dict):
                continue
            value = it.get("trend") or it.get("price") or it.get("avg")
            if value is None:
                continue
            yield SaleRecord(
                source="cardmarket",
                kind="sold",
                sold_at=datetime.now(),
                price=Decimal(str(value)),
                currency=it.get("currency", "EUR"),
                price_usd=None,
                grade_company=None,
                grade=it.get("grade") or "raw",
                condition=it.get("condition"),
                listing_url=it.get("url"),
                raw_payload=it,
            )
