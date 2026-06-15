"""Dragon Ball Super Card Game Masters — Bandai official card list."""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import urljoin, urlparse

from tcgscan_api.sources.http_client import SourceHttpClient

DEFAULT_BASE_URL = "https://www.dbs-cardgame.com/us-en/cardlist/"
NOT_IMPLEMENTED_MESSAGE = (
    "Official Bandai source exists, but clean JSON adapter is not implemented yet"
)

_JSON_CANDIDATES = (
    "cardlist.json",
    "json/cardlist.json",
    "data/cardlist.json",
    "api/cards",
    "api/cardlist",
)


def _base_url() -> str:
    return os.getenv("DRAGON_BALL_MASTERS_BASE_URL", DEFAULT_BASE_URL).strip()


def normalize_card(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "game": "dragon_ball_masters",
        "source": "bandai",
        "source_card_id": raw.get("source_card_id") or raw.get("id") or raw.get("card_id"),
        "name": raw.get("name") or raw.get("card_name"),
        "set_code": raw.get("set_code"),
        "set_name": raw.get("set_name"),
        "card_number": raw.get("card_number") or raw.get("number"),
        "rarity": raw.get("rarity"),
        "card_type": raw.get("card_type") or raw.get("type"),
        "colour": raw.get("colour") or raw.get("color"),
        "cost": raw.get("cost") or raw.get("energy"),
        "power": raw.get("power"),
        "combo_power": raw.get("combo_power"),
        "skills": raw.get("skills"),
        "traits": raw.get("traits"),
        "effect": raw.get("effect") or raw.get("text"),
        "image_url": raw.get("image_url"),
    }


def _sample_from_json(data: Any) -> tuple[str | None, str | None]:
    if isinstance(data, dict):
        items = data.get("cards") or data.get("data") or data.get("items")
        if isinstance(items, list) and items:
            first = items[0]
            if isinstance(first, dict):
                card = normalize_card(first)
                return (
                    str(card.get("name") or "") or None,
                    str(card.get("source_card_id") or "") or None,
                )
        for key in ("name", "card_name"):
            if data.get(key):
                return str(data[key]), str(data.get("id") or data.get("card_id") or "") or None
    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, dict):
            card = normalize_card(first)
            return (
                str(card.get("name") or "") or None,
                str(card.get("source_card_id") or "") or None,
            )
    return None, None


class DragonBallMastersClient:
    provider = "bandai_masters"

    def __init__(self, *, base_url: str | None = None) -> None:
        self.base_url = (base_url or _base_url()).rstrip("/") + "/"
        self._http = SourceHttpClient(rate_per_sec=1.0, burst=2, timeout_s=25.0)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def probe_json_endpoints(self) -> tuple[bool, str, str | None, str | None]:
        parsed = urlparse(self.base_url)
        root = f"{parsed.scheme}://{parsed.netloc}"
        path_prefix = parsed.path.rstrip("/")

        for candidate in _JSON_CANDIDATES:
            for base in (self.base_url, urljoin(root, f"{path_prefix}/")):
                url = urljoin(base, candidate)
                ok, data = await self._http.probe_json_url(url)
                if ok and data is not None:
                    name, card_id = _sample_from_json(data)
                    return True, url, name, card_id
        return False, self.base_url, None, None

    async def diagnostic(self) -> dict[str, Any]:
        try:
            found, source_url, sample_name, sample_id = await self.probe_json_endpoints()
            if found:
                return {
                    "status": "success",
                    "provider": self.provider,
                    "source_url": source_url,
                    "sample_card_name": sample_name,
                    "sample_card_id": sample_id,
                    "message": "Bandai Masters JSON endpoint reachable",
                }

            status_code, final_url, _ = await self._http.get_text(self.base_url)
            if status_code >= 400:
                return {
                    "status": "failed",
                    "provider": self.provider,
                    "source_url": self.base_url,
                    "message": f"Bandai Masters page unreachable (HTTP {status_code})",
                }

            return {
                "status": "not_implemented",
                "provider": self.provider,
                "source_url": final_url,
                "message": NOT_IMPLEMENTED_MESSAGE,
            }
        except Exception as exc:
            return {
                "status": "failed",
                "provider": self.provider,
                "source_url": self.base_url,
                "message": str(exc),
            }
