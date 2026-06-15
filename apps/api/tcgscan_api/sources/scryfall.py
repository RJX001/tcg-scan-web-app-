"""Scryfall API adapter for MTG catalogue ingest."""

from __future__ import annotations

from typing import Any

from tcgscan_api.sources.http_client import SourceHttpClient


def normalize_card(raw: dict[str, Any]) -> dict[str, Any] | None:
    if not raw.get("name") or not raw.get("id"):
        return None
    images = raw.get("image_uris") or {}
    if not images and raw.get("card_faces"):
        faces = raw.get("card_faces") or []
        if faces and isinstance(faces[0], dict):
            images = faces[0].get("image_uris") or {}
    image_url = images.get("large") or images.get("normal")
    return {
        "game": "mtg",
        "source": "scryfall",
        "source_card_id": str(raw["id"]),
        "name": str(raw["name"]),
        "set_code": str(raw.get("set") or "").upper()[:64] or None,
        "set_name": raw.get("set_name"),
        "card_number": str(raw.get("collector_number") or "")[:32] or None,
        "rarity": raw.get("rarity"),
        "image_url": image_url,
        "metadata": {
            "type_line": raw.get("type_line"),
            "mana_cost": raw.get("mana_cost"),
            "cmc": raw.get("cmc"),
            "colors": raw.get("colors"),
            "oracle_text": raw.get("oracle_text"),
        },
        "external_ids": {
            "scryfall_id": str(raw["id"]),
            "tcgplayer_id": raw.get("tcgplayer_id"),
        },
    }


class ScryfallClient:
    def __init__(self) -> None:
        self._http = SourceHttpClient(
            base_url="https://api.scryfall.com",
            rate_per_sec=5.0,
            burst=10,
            timeout_s=30.0,
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def iter_cards(self, *, limit: int) -> list[dict[str, Any]]:
        url: str | None = "/cards/search?q=game%3Apaper&unique=cards&order=set"
        cards: list[dict[str, Any]] = []
        while url and len(cards) < limit:
            payload = await self._http.get_json(
                url,
                cache_key=f"source:scryfall:{url}:{limit}",
                cache_ttl_s=3600,
            )
            data = payload.get("data") if isinstance(payload, dict) else []
            if not isinstance(data, list):
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
            url = payload.get("next_page") if isinstance(payload, dict) and payload.get("has_more") else None
        return cards[:limit]
