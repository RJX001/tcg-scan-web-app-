from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import structlog

from tcgscan_worker.http import ResilientClient
from tcgscan_worker.sources.base import PriceSource, SaleRecord, register
from tcgscan_worker.sources.ebay_auth import get_ebay_oauth_token
from tcgscan_worker.sources.grade_parse import parse_grade_from_text

log = structlog.get_logger()


@register("ebay_sold")
class EbaySoldSource(PriceSource):
    """eBay Marketplace Insights — 90d sold comps. Limited release.

    If `EBAY_INSIGHTS_TOKEN` is missing, log a warning and fall back to Browse API.
    """

    INSIGHTS_URL = "/buy/marketplace_insights/v1_beta/item_sales/search"
    BROWSE_URL = "/buy/browse/v1/item_summary/search"
    BASE_URL = "https://api.ebay.com"

    def _build_client(self) -> ResilientClient:
        marketplace = os.environ.get("EBAY_MARKETPLACE_ID", "EBAY_GB")
        return ResilientClient(
            base_url=self.BASE_URL,
            rate_per_sec=2.0,
            burst=4,
            headers={
                "X-EBAY-C-MARKETPLACE-ID": marketplace,
                "Accept": "application/json",
            },
        )

    async def _auth_headers(self) -> dict[str, str]:
        insights = os.getenv("EBAY_INSIGHTS_TOKEN", "").strip()
        token = insights or await get_ebay_oauth_token()
        return {"Authorization": f"Bearer {token}"}

    async def iter_records(self, *, query: str, limit: int = 100) -> AsyncIterator[SaleRecord]:
        insights_enabled = bool(os.getenv("EBAY_INSIGHTS_TOKEN"))
        if not insights_enabled:
            log.warning(
                "ebay_sold.insights_missing",
                msg="Falling back to Browse-only mode; sold comps may be incomplete",
            )

        url = self.INSIGHTS_URL if insights_enabled else self.BROWSE_URL
        auth = await self._auth_headers()
        emitted = 0
        offset = 0
        page = min(50, limit)
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)

        while emitted < limit:
            params: dict[str, object] = {"q": query, "limit": page, "offset": offset}
            payload = await self.client.get_json(url, params=params, headers=auth)
            items = payload.get("itemSales") or payload.get("itemSummaries") or []
            if not items:
                return
            for it in items:
                price = it.get("lastSoldPrice") or it.get("price") or {}
                value = price.get("value")
                if not value:
                    continue
                currency = price.get("currency") or "USD"
                sold_at_raw = it.get("lastSoldDate") or datetime.now(timezone.utc).isoformat()
                try:
                    sold_at = datetime.fromisoformat(sold_at_raw.replace("Z", "+00:00"))
                except ValueError:
                    sold_at = datetime.now(timezone.utc)
                if sold_at.tzinfo is None:
                    sold_at = sold_at.replace(tzinfo=timezone.utc)
                if sold_at < cutoff:
                    continue
                title = it.get("title") or ""
                parsed = parse_grade_from_text(title)
                yield SaleRecord(
                    source="ebay",
                    kind="sold",
                    sold_at=sold_at,
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
                    return
            if len(items) < page:
                return
            offset += page
