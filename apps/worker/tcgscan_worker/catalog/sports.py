"""Sports cards catalog — tcgapi.dev sports endpoint (MVP top 20k)."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import Any

from tcgscan_worker.catalog.base import CatalogCard, CatalogIngester, register
from tcgscan_worker.http import ResilientClient

SPORT_TO_GAME: dict[str, str] = {
    "baseball": "sports_baseball",
    "basketball": "sports_basketball",
    "football": "sports_football",
    "soccer": "sports_soccer",
}


@register("sports")
class SportsCatalog(CatalogIngester):
    """TCGAPIs / tcgapi.dev sports catalog — paginated MVP ingest."""

    BASE_URL = "https://api.tcgapi.dev/v1"

    def _build_client(self) -> ResilientClient:
        api_key = os.getenv("TCG_API_KEY", "")
        return ResilientClient(
            base_url=self.BASE_URL,
            rate_per_sec=3.0,
            burst=6,
            headers={"Authorization": f"Bearer {api_key}"},
        )

    def _map_game(self, raw: dict[str, Any]) -> str:
        sport = str(raw.get("sport") or raw.get("category") or "baseball").lower()
        return SPORT_TO_GAME.get(sport, "sports_baseball")

    async def iter_cards(self, *, limit: int | None = None) -> AsyncIterator[CatalogCard]:
        emitted = 0
        page = 1
        page_size = 250
        while True:
            payload = await self.client.get_json(
                "/sports/cards",
                params={"page": page, "limit": page_size},
            )
            items = payload.get("data") or payload.get("cards") or []
            if not items:
                return
            for raw in items:
                game = self._map_game(raw)
                images = raw.get("images") or {}
                image_urls = {
                    k: str(v)
                    for k, v in {
                        "small": images.get("small") or raw.get("image_small"),
                        "large": images.get("large") or raw.get("image"),
                        "front": raw.get("image_url"),
                    }.items()
                    if v
                }
                yield CatalogCard(
                    game=game,
                    name=str(raw.get("name") or raw.get("player") or "Unknown"),
                    set_code=str(raw.get("set_code") or raw.get("set") or "")[:64] or None,
                    set_name=raw.get("set_name"),
                    number=str(raw.get("number") or raw.get("card_number") or "")[:32] or None,
                    rarity=raw.get("rarity"),
                    image_urls=image_urls,
                    external_ids={
                        k: str(v)
                        for k, v in {
                            "tcgapi_id": raw.get("id"),
                            "tcgplayer_id": raw.get("tcgplayer_id"),
                        }.items()
                        if v
                    },
                    attributes={
                        k: v
                        for k, v in {
                            "player": raw.get("player"),
                            "year": raw.get("year"),
                            "manufacturer": raw.get("manufacturer"),
                            "sport": raw.get("sport"),
                            "team": raw.get("team"),
                        }.items()
                        if v is not None
                    },
                    variants={},
                )
                emitted += 1
                if limit is not None and emitted >= limit:
                    return
            if len(items) < page_size:
                return
            page += 1
