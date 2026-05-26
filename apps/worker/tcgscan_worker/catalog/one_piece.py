from __future__ import annotations

from collections.abc import AsyncIterator

from tcgscan_worker.catalog.base import CatalogCard, CatalogIngester, register
from tcgscan_worker.http import ResilientClient


@register("one_piece")
class OnePieceCatalog(CatalogIngester):
    """One Piece CG — community Scryfall-style endpoint."""

    BASE_URL = "https://optcgapi.com"

    def _build_client(self) -> ResilientClient:
        return ResilientClient(base_url=self.BASE_URL, rate_per_sec=2.0, burst=4)

    async def iter_cards(self, *, limit: int | None = None) -> AsyncIterator[CatalogCard]:
        payload = await self.client.get_json("/api/allCards/")
        data = payload.get("data") or []
        emitted = 0
        for raw in data:
            yield CatalogCard(
                game="one_piece",
                name=str(raw.get("name") or ""),
                set_code=str(raw.get("set_code") or raw.get("set_id") or "")[:64] or None,
                set_name=raw.get("set_name"),
                number=str(raw.get("card_number") or raw.get("id") or "")[:32] or None,
                rarity=raw.get("rarity"),
                image_urls={"large": raw.get("image_url") or raw.get("image")},
                external_ids={"optcgapi_id": str(raw.get("id", ""))},
                attributes={
                    "color": raw.get("color"),
                    "cost": raw.get("cost"),
                    "power": raw.get("power"),
                    "counter": raw.get("counter"),
                    "type": raw.get("type"),
                },
                variants={},
            )
            emitted += 1
            if limit is not None and emitted >= limit:
                return
