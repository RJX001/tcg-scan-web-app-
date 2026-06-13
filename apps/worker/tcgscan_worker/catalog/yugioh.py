from __future__ import annotations

from collections.abc import AsyncIterator

from tcgscan_worker.catalog.base import CatalogCard, CatalogIngester, register
from tcgscan_worker.http import ResilientClient


@register("yugioh")
class YugiohCatalog(CatalogIngester):
    """YGOPRODeck — free, single-shot 'cardinfo.php' returns everything."""

    BASE_URL = "https://db.ygoprodeck.com/api/v7"

    def _build_client(self) -> ResilientClient:
        return ResilientClient(base_url=self.BASE_URL, rate_per_sec=2.0, burst=4, timeout_s=60.0)

    async def iter_cards(self, *, limit: int | None = None) -> AsyncIterator[CatalogCard]:
        payload = await self.client.get_json("/cardinfo.php")
        data = payload.get("data") or []
        emitted = 0
        for raw in data:
            sets = raw.get("card_sets") or [{}]
            images = raw.get("card_images") or [{}]
            first_image = images[0] if images else {}
            image_urls = {
                k: v
                for k, v in {
                    "small": first_image.get("image_url_small"),
                    "large": first_image.get("image_url"),
                }.items()
                if v
            }
            for card_set in sets:
                set_code = str(card_set.get("set_code") or "")[:64] or None
                yield CatalogCard(
                    game="yugioh",
                    name=str(raw.get("name") or ""),
                    set_code=set_code,
                    set_name=card_set.get("set_name"),
                    number=set_code[:32] if set_code else None,
                    rarity=card_set.get("set_rarity"),
                    image_urls=image_urls,
                    external_ids={"ygoprodeck_id": str(raw.get("id", ""))},
                    attributes={
                        "type": raw.get("type"),
                        "atk": raw.get("atk"),
                        "def": raw.get("def"),
                        "level": raw.get("level"),
                        "race": raw.get("race"),
                        "attribute": raw.get("attribute"),
                    },
                    variants={},
                )
                emitted += 1
                if limit is not None and emitted >= limit:
                    return
