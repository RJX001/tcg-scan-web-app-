from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import Any

from tcgscan_worker.catalog.base import CatalogCard, CatalogIngester, register
from tcgscan_worker.http import ResilientClient


@register("pokemon")
class PokemonCatalog(CatalogIngester):
    """pokemontcg.io — free API, ~250 req/min recommended."""

    BASE_URL = "https://api.pokemontcg.io/v2"

    def _build_client(self) -> ResilientClient:
        headers = {}
        api_key = os.getenv("POKEMONTCG_API_KEY")
        if api_key:
            headers["X-Api-Key"] = api_key
        return ResilientClient(base_url=self.BASE_URL, rate_per_sec=4.0, burst=8, headers=headers)

    async def iter_cards(self, *, limit: int | None = None) -> AsyncIterator[CatalogCard]:
        page = 1
        page_size = 250
        emitted = 0
        while True:
            payload = await self.client.get_json(
                "/cards", params={"page": page, "pageSize": page_size}
            )
            data = payload.get("data") or []
            if not data:
                return
            for raw in data:
                card = _to_card(raw)
                if card is None:
                    continue
                yield card
                emitted += 1
                if limit is not None and emitted >= limit:
                    return
            if len(data) < page_size:
                return
            page += 1


def _to_card(raw: dict[str, Any]) -> CatalogCard | None:
    if not raw.get("name") or not raw.get("id"):
        return None
    set_info = raw.get("set") or {}
    images = raw.get("images") or {}
    return CatalogCard(
        game="pokemon",
        name=str(raw["name"]),
        set_code=str(set_info.get("id") or set_info.get("ptcgoCode") or "")[:64] or None,
        set_name=set_info.get("name"),
        number=str(raw.get("number") or "")[:32] or None,
        rarity=raw.get("rarity"),
        image_urls={
            k: v
            for k, v in {"small": images.get("small"), "large": images.get("large")}.items()
            if v
        },
        external_ids={"pokemontcg_io": str(raw["id"])},
        attributes={
            "hp": raw.get("hp"),
            "types": raw.get("types"),
            "supertype": raw.get("supertype"),
            "subtypes": raw.get("subtypes"),
        },
        variants={},
    )
