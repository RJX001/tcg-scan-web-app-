from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from tcgscan_worker.catalog.base import CatalogCard, CatalogIngester, register
from tcgscan_worker.http import ResilientClient


@register("mtg")
class MtgCatalog(CatalogIngester):
    """Scryfall — free, 10 req/s ceiling but be polite (~5 req/s)."""

    BASE_URL = "https://api.scryfall.com"

    def _build_client(self) -> ResilientClient:
        return ResilientClient(
            base_url=self.BASE_URL,
            rate_per_sec=5.0,
            burst=10,
            headers={"User-Agent": "tcgscan/0.0.0", "Accept": "application/json"},
        )

    async def iter_cards(self, *, limit: int | None = None) -> AsyncIterator[CatalogCard]:
        url: str | None = "/cards/search?q=game%3Apaper&unique=cards&order=set"
        emitted = 0
        while url:
            payload = await self.client.get_json(url)
            data = payload.get("data") or []
            for raw in data:
                card = _to_card(raw)
                if card is None:
                    continue
                yield card
                emitted += 1
                if limit is not None and emitted >= limit:
                    return
            url = payload.get("next_page") if payload.get("has_more") else None


def _to_card(raw: dict[str, Any]) -> CatalogCard | None:
    if not raw.get("name") or not raw.get("id"):
        return None
    images = raw.get("image_uris") or {}
    return CatalogCard(
        game="mtg",
        name=str(raw["name"]),
        set_code=(raw.get("set") or "").upper()[:64] or None,
        set_name=raw.get("set_name"),
        number=str(raw.get("collector_number") or "")[:32] or None,
        rarity=raw.get("rarity"),
        image_urls={
            k: v
            for k, v in {
                "small": images.get("small"),
                "normal": images.get("normal"),
                "large": images.get("large"),
            }.items()
            if v
        },
        external_ids={
            "scryfall_id": str(raw["id"]),
            "oracle_id": str(raw.get("oracle_id", "")),
            "tcgplayer_id": str(raw.get("tcgplayer_id") or ""),
        },
        attributes={
            "mana_cost": raw.get("mana_cost"),
            "type_line": raw.get("type_line"),
            "colors": raw.get("colors"),
            "cmc": raw.get("cmc"),
        },
        variants={},
    )
