"""Shared agent tools — pricing lookups (stubs wired to internal patterns)."""

from __future__ import annotations

from typing import Any


async def fetch_comps_summary(card_id: str, *, days: int = 30) -> dict[str, Any]:
    """Return comp summary for PricingAgent. Wire to SalesRepo in production."""
    return {"card_id": card_id, "days": days, "count": 0, "median_usd": None}


async def fetch_active_listings(card_id: str) -> list[dict[str, Any]]:
    return []


async def grading_cost_usd(company: str = "PSA") -> float:
    return 25.0 if company == "PSA" else 20.0
