"""Map normalised source payloads to card_identity rows."""

from __future__ import annotations

from typing import Any

from tcgscan_api.db.models import Game


def _game_enum(game: str) -> Game:
    return Game(game)


def to_card_identity_row(normalized: dict[str, Any]) -> dict[str, Any]:
    image_url = normalized.get("image_url")
    image_urls: dict[str, str] = {}
    if isinstance(image_url, str) and image_url:
        image_urls = {"large": image_url, "front": image_url}

    metadata = normalized.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {
            k: normalized[k]
            for k in (
                "card_type",
                "race",
                "attribute",
                "archetype",
                "level",
                "rank",
                "linkval",
                "atk",
                "def",
                "description",
                "colour",
                "cost",
                "power",
                "counter",
                "family",
                "effect",
                "trigger",
                "traits",
                "skills",
                "combo_power",
            )
            if normalized.get(k) is not None
        }

    number = normalized.get("card_number") or normalized.get("number")
    external_ids = normalized.get("external_ids")
    if not isinstance(external_ids, dict):
        external_ids = {}

    return {
        "game": _game_enum(str(normalized["game"])),
        "source": str(normalized["source"]),
        "source_card_id": str(normalized["source_card_id"]),
        "name": str(normalized["name"])[:255],
        "set_code": (str(normalized["set_code"])[:64] if normalized.get("set_code") else None),
        "set_name": (str(normalized["set_name"])[:255] if normalized.get("set_name") else None),
        "number": (str(number)[:32] if number else None),
        "rarity": (str(normalized["rarity"])[:64] if normalized.get("rarity") else None),
        "attributes": metadata,
        "image_urls": image_urls,
        "external_ids": external_ids,
        "variants": {},
    }
