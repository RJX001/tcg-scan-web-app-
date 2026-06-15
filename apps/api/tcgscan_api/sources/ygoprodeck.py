"""YGOPRODeck public API adapter — no API key required."""

from __future__ import annotations

import os
from typing import Any

from tcgscan_api.sources.http_client import SourceHttpClient

DEFAULT_BASE_URL = "https://db.ygoprodeck.com/api/v7"


def _base_url() -> str:
    return os.getenv("YGOPRODECK_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def normalize_card(raw: dict[str, Any]) -> dict[str, Any]:
    images = raw.get("card_images") or [{}]
    first_image = images[0] if images else {}
    card_sets = raw.get("card_sets") or []
    first_set = card_sets[0] if card_sets else {}
    card_prices = raw.get("card_prices") or [{}]
    first_price = card_prices[0] if card_prices else {}

    price_usd = first_price.get("tcgplayer_price") or first_price.get("amazon_price")
    price_eur = first_price.get("cardmarket_price")

    return {
        "game": "yu_gi_oh",
        "source": "ygoprodeck",
        "source_card_id": str(raw.get("id", "")),
        "name": raw.get("name"),
        "card_type": raw.get("type"),
        "race": raw.get("race"),
        "attribute": raw.get("attribute"),
        "archetype": raw.get("archetype"),
        "level": raw.get("level"),
        "rank": raw.get("rank"),
        "linkval": raw.get("linkval"),
        "atk": raw.get("atk"),
        "def": raw.get("def"),
        "description": raw.get("desc"),
        "set_code": first_set.get("set_code"),
        "set_name": first_set.get("set_name"),
        "rarity": first_set.get("set_rarity"),
        "image_url": first_image.get("image_url"),
        "price_usd": price_usd,
        "price_eur": price_eur,
    }


class YgoProDeckClient:
    def __init__(self, *, base_url: str | None = None) -> None:
        url = (base_url or _base_url()).rstrip("/")
        self.base_url = url
        self._http = SourceHttpClient(base_url=url, rate_per_sec=2.0, burst=4, timeout_s=30.0)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def get_all_cards(self) -> list[dict[str, Any]]:
        payload = await self._http.get_json(
            "/cardinfo.php",
            cache_key="source:ygoprodeck:all_cards",
            cache_ttl_s=3600,
        )
        data = payload.get("data") if isinstance(payload, dict) else payload
        return list(data or [])

    async def search_card(self, name: str) -> list[dict[str, Any]]:
        payload = await self._http.get_json(
            "/cardinfo.php",
            params={"name": name},
            cache_key=f"source:ygoprodeck:search:{name.lower()}",
            cache_ttl_s=3600,
        )
        data = payload.get("data") if isinstance(payload, dict) else payload
        return list(data or [])

    async def get_card_by_id(self, card_id: str | int) -> list[dict[str, Any]]:
        payload = await self._http.get_json(
            "/cardinfo.php",
            params={"id": str(card_id)},
            cache_key=f"source:ygoprodeck:id:{card_id}",
            cache_ttl_s=3600,
        )
        data = payload.get("data") if isinstance(payload, dict) else payload
        return list(data or [])

    async def diagnostic(self) -> dict[str, Any]:
        try:
            cards = await self.search_card("Dark Magician")
            if not cards:
                return {
                    "status": "failed",
                    "provider": "ygoprodeck",
                    "source_url": f"{self.base_url}/cardinfo.php",
                    "message": "YGOPRODeck reachable but no sample card returned",
                }
            sample = normalize_card(cards[0])
            return {
                "status": "success",
                "provider": "ygoprodeck",
                "source_url": f"{self.base_url}/cardinfo.php",
                "sample_card_name": sample.get("name"),
                "sample_card_id": sample.get("source_card_id"),
                "message": f"YGOPRODeck reachable ({len(cards)} card(s) matched)",
            }
        except Exception as exc:
            return {
                "status": "failed",
                "provider": "ygoprodeck",
                "source_url": f"{self.base_url}/cardinfo.php",
                "message": str(exc),
            }
