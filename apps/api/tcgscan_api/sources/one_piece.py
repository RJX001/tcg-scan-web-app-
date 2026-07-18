"""One Piece TCG — OPTCG API adapter (no API key required)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import httpx
import structlog

from tcgscan_api.sources.http_client import SourceHttpClient

log = structlog.get_logger()

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


@dataclass(frozen=True)
class OnePieceCatalogResult:
    cards: list[dict[str, Any]]
    skipped_optional_endpoints: tuple[str, ...] = field(default_factory=tuple)

    @property
    def optional_skip_count(self) -> int:
        return len(self.skipped_optional_endpoints)

    @property
    def optional_skip_message(self) -> str | None:
        if not self.skipped_optional_endpoints:
            return None
        labels = ", ".join(self.skipped_optional_endpoints)
        if any("promo" in label.lower() for label in self.skipped_optional_endpoints):
            return "Promo endpoint unavailable/skipped."
        return f"Optional endpoints unavailable/skipped: {labels}."


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

    async def _fetch_endpoint_rows(
        self,
        fetch: Any,
        *,
        label: str,
        optional: bool,
    ) -> tuple[list[dict[str, Any]], str | None]:
        try:
            return await fetch(), None
        except httpx.HTTPStatusError as exc:
            if not optional:
                raise
            skip_label = f"{label} ({exc.response.status_code})"
            log.warning(
                "one_piece.optional_endpoint_skipped",
                endpoint=label,
                status=exc.response.status_code,
            )
            return [], skip_label
        except httpx.HTTPError as exc:
            if not optional:
                raise
            skip_label = f"{label} (unavailable)"
            log.warning("one_piece.optional_endpoint_skipped", endpoint=label, error=str(exc))
            return [], skip_label

    async def iter_all_cards(self, *, limit: int | None = None) -> OnePieceCatalogResult:
        seen: set[str] = set()
        cards: list[dict[str, Any]] = []
        skipped_optional: list[str] = []
        fetchers: list[tuple[Any, str, bool]] = [
            (self.get_all_set_cards, "allSetCards", False),
            (self.get_starter_deck_cards, "allSTCards", False),
            (self.get_promo_cards, "allPromoCards", True),
            (self.get_don_cards, "allDonCards", True),
        ]
        for fetch, label, optional in fetchers:
            rows, skip_label = await self._fetch_endpoint_rows(
                fetch, label=label, optional=optional
            )
            if skip_label:
                skipped_optional.append(skip_label)
                continue
            for raw in rows:
                normalized = normalize_card(raw)
                sid = str(normalized.get("source_card_id") or "")
                if not sid or sid in seen:
                    continue
                seen.add(sid)
                cards.append(normalized)
                if limit is not None and len(cards) >= limit:
                    return OnePieceCatalogResult(
                        cards=cards, skipped_optional_endpoints=tuple(skipped_optional)
                    )
        return OnePieceCatalogResult(
            cards=cards, skipped_optional_endpoints=tuple(skipped_optional)
        )

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
