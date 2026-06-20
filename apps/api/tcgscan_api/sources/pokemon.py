"""Pokémon TCG API adapter for catalogue ingest."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx
import structlog

from tcgscan_api.sources.http_client import SourceHttpClient

log = structlog.get_logger()

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
            "tcgplayer": raw.get("tcgplayer"),
            "cardmarket": raw.get("cardmarket"),
        },
        "external_ids": {"pokemontcg_id": str(raw["id"])},
    }


@dataclass(frozen=True)
class PokemonPageResult:
    cards: list[dict[str, Any]]
    has_more: bool
    next_page: int
    page_failed: bool = False


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

    async def fetch_page(self, *, page: int, page_size: int) -> PokemonPageResult:
        page = max(1, page)
        page_size = max(1, min(page_size, 250))
        try:
            payload = await self._http.get_json(
                "/cards",
                params={"page": page, "pageSize": page_size},
                cache_key=f"source:pokemon:cards:p{page}:s{page_size}",
                cache_ttl_s=3600,
            )
        except httpx.HTTPStatusError as exc:
            log.warning(
                "pokemon.page_fetch_failed",
                page=page,
                status=exc.response.status_code,
            )
            return PokemonPageResult(cards=[], has_more=True, next_page=page + 1, page_failed=True)
        except httpx.HTTPError as exc:
            log.warning("pokemon.page_fetch_failed", page=page, error=str(exc))
            return PokemonPageResult(cards=[], has_more=True, next_page=page + 1, page_failed=True)

        data = payload.get("data") if isinstance(payload, dict) else []
        if not isinstance(data, list):
            data = []
        cards: list[dict[str, Any]] = []
        for raw in data:
            if not isinstance(raw, dict):
                continue
            normalized = normalize_card(raw)
            if normalized is not None:
                cards.append(normalized)

        total_count = payload.get("totalCount") if isinstance(payload, dict) else None
        if isinstance(total_count, int) and total_count >= 0:
            fetched_so_far = (page - 1) * page_size + len(data)
            has_more = fetched_so_far < total_count and len(data) > 0
        else:
            has_more = len(data) >= page_size
        return PokemonPageResult(cards=cards, has_more=has_more, next_page=page + 1)

    async def iter_cards(self, *, limit: int | None = 100) -> list[dict[str, Any]]:
        page = 1
        page_size = 250 if limit is None or limit > 250 else min(limit, 250)
        cards: list[dict[str, Any]] = []
        while limit is None or len(cards) < limit:
            result = await self.fetch_page(page=page, page_size=page_size)
            if result.page_failed and not result.cards:
                page = result.next_page
                if page > 500:
                    break
                continue
            cards.extend(result.cards)
            if limit is not None and len(cards) >= limit:
                break
            if not result.has_more:
                break
            page = result.next_page
        return cards if limit is None else cards[:limit]
