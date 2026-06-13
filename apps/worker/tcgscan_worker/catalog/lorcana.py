from __future__ import annotations

from collections.abc import AsyncIterator

from tcgscan_worker.catalog.base import CatalogCard, CatalogIngester, register
from tcgscan_worker.http import ResilientClient


@register("lorcana")
class LorcanaCatalog(CatalogIngester):
    """Lorcast — community, free; modest rate limit."""

    BASE_URL = "https://api.lorcast.com/v0"

    def _build_client(self) -> ResilientClient:
        return ResilientClient(base_url=self.BASE_URL, rate_per_sec=2.0, burst=4)

    async def iter_cards(self, *, limit: int | None = None) -> AsyncIterator[CatalogCard]:
        page = 1
        emitted = 0
        while True:
            payload = await self.client.get_json("/cards/search", params={"q": "*", "page": page})
            results = payload.get("results") or payload.get("data") or []
            if not results:
                return
            for raw in results:
                yield CatalogCard(
                    game="lorcana",
                    name=str(raw.get("name") or ""),
                    set_code=str((raw.get("set") or {}).get("code") or "")[:64] or None,
                    set_name=(raw.get("set") or {}).get("name"),
                    number=str(raw.get("collector_number") or "")[:32] or None,
                    rarity=raw.get("rarity"),
                    image_urls={
                        "large": (raw.get("image_uris") or {}).get("digital", {}).get("large")
                    },
                    external_ids={"lorcast_id": str(raw.get("id", ""))},
                    attributes={
                        "cost": raw.get("cost"),
                        "ink_cost": raw.get("ink_cost"),
                        "ink_type": raw.get("ink"),
                        "type": raw.get("type"),
                    },
                    variants={},
                )
                emitted += 1
                if limit is not None and emitted >= limit:
                    return
            if not payload.get("has_more"):
                return
            page += 1
