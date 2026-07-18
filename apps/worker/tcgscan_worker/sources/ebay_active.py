from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import datetime
from decimal import Decimal

import structlog

from tcgscan_worker.http import ResilientClient
from tcgscan_worker.sources.base import PriceSource, SaleRecord, register
from tcgscan_worker.sources.ebay_auth import get_ebay_oauth_token
from tcgscan_worker.sources.grade_parse import parse_grade_from_text

log = structlog.get_logger()


@register("ebay_active")
class EbayActiveSource(PriceSource):
    """eBay Browse API — active listings."""

    BASE_URL = "https://api.ebay.com"

    def _build_client(self) -> ResilientClient:
        marketplace = os.environ.get("EBAY_MARKETPLACE_ID", "EBAY_GB")
        return ResilientClient(
            base_url=self.BASE_URL,
            rate_per_sec=5.0,
            burst=10,
            headers={
                "X-EBAY-C-MARKETPLACE-ID": marketplace,
                "Accept": "application/json",
            },
        )

    async def _auth_headers(self) -> dict[str, str]:
        token = await get_ebay_oauth_token()
        return {"Authorization": f"Bearer {token}"}

    async def iter_records(self, *, query: str, limit: int = 100) -> AsyncIterator[SaleRecord]:
        emitted = 0
        pages = 0
        offset = 0
        page = 50
        auth = await self._auth_headers()
        while emitted < limit:
            payload = await self.client.get_json(
                "/buy/browse/v1/item_summary/search",
                params={"q": query, "limit": page, "offset": offset, "category_ids": "183454"},
                headers=auth,
            )
            pages += 1
            items = payload.get("itemSummaries") or []
            if not items:
                log.debug("ebay_active.fetch.done", pages=pages, emitted=emitted)
                return
            for it in items:
                price = it.get("price") or {}
                value = price.get("value")
                if not value:
                    continue
                currency = price.get("currency") or "USD"
                title = it.get("title") or ""
                parsed = parse_grade_from_text(title)
                yield SaleRecord(
                    source="ebay",
                    kind="listing",
                    sold_at=datetime.now(),
                    price=Decimal(str(value)),
                    currency=currency,
                    price_usd=Decimal(str(value)) if currency == "USD" else None,
                    grade_company=parsed.grade_company,
                    grade=parsed.grade,
                    condition=it.get("condition"),
                    listing_url=it.get("itemWebUrl"),
                    raw_payload=it,
                )
                emitted += 1
                if emitted >= limit:
                    log.debug("ebay_active.fetch.done", pages=pages, emitted=emitted)
                    return
            if len(items) < page:
                log.debug("ebay_active.fetch.done", pages=pages, emitted=emitted)
                return
            offset += page
