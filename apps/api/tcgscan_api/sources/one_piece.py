"""One Piece TCG — OPTCG API adapter (no API key required)."""

from __future__ import annotations

import os
from typing import Any

from tcgscan_api.sources.http_client import SourceHttpClient

DEFAULT_BASE_URL = "https://optcgapi.com"


def _base_url() -> str:
    return os.getenv("ONE_PIECE_API_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def normalize_card(raw: dict[str, Any]) -> dict[str, Any]:
    card_id = raw.get("card_set_id") or raw.get("card_image_id") or raw.get("id")
    image = raw.get("card_image") or raw.get("image_url") or raw.get("image")
    return {
        "game": "one_piece",
        "source": "optcgapi",
        "source_card_id": str(card_id or ""),
        "name": raw.get("card_name") or raw.get("name"),
        "set_code": raw.get("set_id") or raw.get("set_code"),
        "set_name": raw.get("set_name"),
        "card_number": raw.get("card_set_id") or raw.get("card_number"),
        "rarity": raw.get("rarity"),
        "colour": raw.get("card_color") or raw.get("color"),
        "card_type": raw.get("card_type") or raw.get("type"),
        "cost": raw.get("card_cost") or raw.get("cost"),
        "power": raw.get("card_power") or raw.get("power"),
        "counter": raw.get("counter_amount") or raw.get("counter"),
        "attribute": raw.get("attribute"),
        "family": raw.get("sub_types") or raw.get("types"),
        "effect": raw.get("card_text") or raw.get("effect"),
        "trigger": raw.get("trigger"),
        "image_url": image,
    }


class OnePieceClient:
    def __init__(self, *, base_url: str | None = None) -> None:
        url = (base_url or _base_url()).rstrip("/")
        self.base_url = url
        self._http = SourceHttpClient(base_url=url, rate_per_sec=4.0, burst=8, timeout_s=30.0)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _get_list(self, path: str, *, cache_key: str) -> list[dict[str, Any]]:
        payload = await self._http.get_json(path, cache_key=cache_key, cache_ttl_s=3600)
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            data = payload.get("data")
            if isinstance(data, list):
                return [item for item in data if isinstance(item, dict)]
        return []

    async def get_all_sets(self) -> list[dict[str, Any]]:
        return await self._get_list("/api/allSets/", cache_key="source:optcg:all_sets")

    async def get_all_set_cards(self) -> list[dict[str, Any]]:
        return await self._get_list("/api/allSetCards/", cache_key="source:optcg:all_set_cards")

    async def get_set(self, set_id: str) -> list[dict[str, Any]]:
        return await self._get_list(
            f"/api/sets/{set_id}/",
            cache_key=f"source:optcg:set:{set_id}",
        )

    async def get_card(self, card_id: str) -> list[dict[str, Any]]:
        return await self._get_list(
            f"/api/sets/card/{card_id}/",
            cache_key=f"source:optcg:card:{card_id}",
        )

    async def get_starter_decks(self) -> list[dict[str, Any]]:
        return await self._get_list("/api/allDecks/", cache_key="source:optcg:all_decks")

    async def get_starter_deck_cards(self) -> list[dict[str, Any]]:
        return await self._get_list("/api/allSTCards/", cache_key="source:optcg:all_st_cards")

    async def get_promo_cards(self) -> list[dict[str, Any]]:
        return await self._get_list("/api/allPromoCards/", cache_key="source:optcg:all_promo_cards")

    async def get_don_cards(self) -> list[dict[str, Any]]:
        return await self._get_list("/api/allDonCards/", cache_key="source:optcg:all_don_cards")

    async def iter_all_cards(self, *, limit: int | None = None) -> list[dict[str, Any]]:
        seen: set[str] = set()
        cards: list[dict[str, Any]] = []
        fetchers = [
            self.get_all_set_cards,
            self.get_starter_deck_cards,
            self.get_promo_cards,
            self.get_don_cards,
        ]
        for fetch in fetchers:
            rows = await fetch()
            for raw in rows:
                normalized = normalize_card(raw)
                sid = str(normalized.get("source_card_id") or "")
                if not sid or sid in seen:
                    continue
                seen.add(sid)
                cards.append(normalized)
                if limit is not None and len(cards) >= limit:
                    return cards
        return cards

    async def diagnostic(self) -> dict[str, Any]:
        try:
            sets = await self.get_all_sets()
            cards = await self.get_card("OP01-077")
            sample = normalize_card(cards[0]) if cards else None
            if sample is None and sets:
                set_cards = await self.get_set(str(sets[0].get("set_id", "OP-01")))
                if set_cards:
                    sample = normalize_card(set_cards[0])

            if sample is None:
                return {
                    "status": "failed",
                    "provider": "optcgapi",
                    "source_url": self.base_url,
                    "set_count": len(sets),
                    "message": "OPTCG API reachable but no sample card could be loaded",
                }

            return {
                "status": "success",
                "provider": "optcgapi",
                "source_url": self.base_url,
                "sample_card_name": sample.get("name"),
                "sample_card_id": sample.get("source_card_id"),
                "set_count": len(sets),
                "message": f"OPTCG API reachable ({len(sets)} sets)",
            }
        except Exception as exc:
            return {
                "status": "failed",
                "provider": "optcgapi",
                "source_url": self.base_url,
                "message": str(exc),
            }
