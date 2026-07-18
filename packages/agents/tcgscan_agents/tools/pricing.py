"""Shared agent tools — pricing lookups via internal API."""

from __future__ import annotations

import os
from typing import Any

import httpx
import structlog

log = structlog.get_logger()


def _api_base() -> str:
    return os.getenv("TCGSCAN_API_URL", os.getenv("API_PUBLIC_URL", "http://localhost:8000"))


async def fetch_comps_summary(card_id: str, *, days: int = 30) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(
                f"{_api_base()}/v1/cards/{card_id}/comps/summary", params={"days": days}
            )
            if r.status_code != 200:
                log.warning(
                    "tool.pricing.comps_failed",
                    card_id=card_id,
                    status_code=r.status_code,
                )
                return {"card_id": card_id, "days": days, "count": 0, "median_usd": None}
            data = r.json()
            return {
                "card_id": card_id,
                "days": days,
                "count": data.get("count", 0),
                "median_usd": data.get("median_usd"),
                "mean_usd": data.get("mean_usd"),
            }
    except httpx.HTTPError as exc:
        log.warning("tool.pricing.request_failed", card_id=card_id, error=str(exc))
        raise


async def fetch_active_listings(card_id: str) -> list[dict[str, Any]]:
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(f"{_api_base()}/v1/cards/{card_id}/listings")
            if r.status_code != 200:
                log.warning(
                    "tool.pricing.listings_failed",
                    card_id=card_id,
                    status_code=r.status_code,
                )
                return []
            raw = r.json()
            if not isinstance(raw, list):
                log.warning(
                    "tool.pricing.listings_failed",
                    card_id=card_id,
                    status_code=r.status_code,
                )
                return []
            listings: list[dict[str, Any]] = []
            for item in raw:
                if isinstance(item, dict):
                    listings.append(item)
            return listings
    except httpx.HTTPError as exc:
        log.warning("tool.pricing.request_failed", card_id=card_id, error=str(exc))
        raise


async def grading_cost_usd(company: str = "PSA") -> float:
    return 25.0 if company == "PSA" else 20.0
