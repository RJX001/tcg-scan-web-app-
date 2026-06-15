"""Pokémon TCG API adapter for catalogue ingest."""

from __future__ import annotations

import os
from typing import Any

from tcgscan_api.sources.http_client import SourceHttpClient

DEFAULT_BASE_URL = "https://api.pokemontcg.io/v2"


def _base_url() -> str:
    return os.getenv("POKEMONTCG_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def normalize_card(raw: dict[str, Any]) -> dict[str, Any] | None:
    if not raw.get("name") or not raw.get("id"):
        return None
    set_info = raw.get("set") or {}
    images = raw.get("images") or {}
    image_url = images.get("large") or images.get("small")
    return {
        "game": "pokemon",
        "source": "pokemontcg",
        "source_card_id": str(raw["id"]),
        "name": str(raw["name"]),
        "set_code": str(set_info.get("id") or set_info.get("ptcgoCode") or "")[:64] or None,
        "set_name": set_info.get("name"),
        "card_number": str(raw.get("number") or "")[:32] or None,
        "rarity": raw.get("rarity"),
        "image_url": image_url,
        "metadata": {
            "supertype": raw.get("supertype"),
            "subtypes": raw.get("subtypes"),
            "hp": raw.get("hp"),
            "types": raw.get("types"),
            "artist": raw.get("artist"),
            "legalities": raw.get("legalities"),
        },
        "external_ids": {"pokemontcg_id": str(raw["id"])},
    }


class PokemonClient:
    def __init__(self, *, base_url: str | None = None) -> None:
        url = (base_url or _base_url()).rstrip("/")
        headers: dict[str, str] = {}
        api_key = os.getenv("POKEMONTCG_API_KEY", "").strip()
        if api_key:
            headers["X-Api-Key"] = api_key
        self._http = SourceHttpClient(base_url=url, rate_per_sec=4.0, burst=8, headers=headers, timeout_s=30.0)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def iter_cards(self, *, limit: int) -> list[dict[str, Any]]:
        page = 1
        page_size = min(limit, 250)
        cards: list[dict[str, Any]] = []
        while len(cards) < limit:
            payload = await self._http.get_json(
                "/cards",
                params={"page": page, "pageSize": page_size},
                cache_key=f"source:pokemon:cards:p{page}:s{page_size}",
                cache_ttl_s=3600,
            )
            data = payload.get("data") if isinstance(payload, dict) else []
            if not isinstance(data, list) or not data:
                break
            for raw in data:
                if not isinstance(raw, dict):
                    continue
                normalized = normalize_card(raw)
                if normalized is None:
                    continue
                cards.append(normalized)
                if len(cards) >= limit:
                    break
            if len(data) < page_size:
                break
            page += 1
        return cards[:limit]
