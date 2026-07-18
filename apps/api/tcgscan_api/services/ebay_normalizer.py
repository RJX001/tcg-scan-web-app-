"""Normalise eBay Browse API item summaries into marketplace_listings rows."""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from typing import Any

from tcgscan_api.config import Settings, get_settings
from tcgscan_api.services.ebay_affiliate import build_ebay_affiliate_url

_GRADE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("PSA", re.compile(r"\bPSA\s*(\d+(?:\.\d+)?)\b", re.I)),
    ("BGS", re.compile(r"\b(?:BGS|BECKETT)\s*(\d+(?:\.\d+)?)\b", re.I)),
    ("CGC", re.compile(r"\bCGC\s*(\d+(?:\.\d+)?)\b", re.I)),
    ("ACE", re.compile(r"\bACE\s*(\d+(?:\.\d+)?)\b", re.I)),
    ("SGC", re.compile(r"\bSGC\s*(\d+(?:\.\d+)?)\b", re.I)),
]


def _parse_grade(title: str) -> str | None:
    for company, pattern in _GRADE_PATTERNS:
        match = pattern.search(title)
        if match:
            return f"{company} {match.group(1)}"
    return None


def _affiliate_url(item_url: str, settings: Settings) -> tuple[str, str]:
    tracking = (settings.ebay_affiliate_tracking_id or "").strip()
    campaign = (settings.ebay_affiliate_campaign_id or "").strip()
    if tracking and campaign:
        return build_ebay_affiliate_url(
            item_url, tracking_id=tracking, campaign_id=campaign
        ), "configured"
    return item_url, "not_configured"


def normalize_ebay_item_summary(
    item: dict[str, Any],
    *,
    marketplace: str,
    settings: Settings | None = None,
    observed_at: datetime | None = None,
) -> dict[str, Any] | None:
    """Map a Browse API item summary to a marketplace_listings upsert row."""
    settings = settings or get_settings()
    item_id = item.get("itemId") or item.get("legacyItemId")
    if not item_id:
        return None
    price_obj = item.get("price") or {}
    value = price_obj.get("value")
    if value is None:
        return None
    item_url = item.get("itemWebUrl")
    if not item_url or not isinstance(item_url, str):
        return None
    title = str(item.get("title") or "").strip()
    if not title:
        return None
    currency = str(price_obj.get("currency") or "USD")
    outbound_url, affiliate_status = _affiliate_url(item_url, settings)
    seller = item.get("seller") or {}
    seller_username = seller.get("username") if isinstance(seller, dict) else None
    image = item.get("image") or {}
    image_url = image.get("imageUrl") if isinstance(image, dict) else None
    now = observed_at or datetime.now()
    return {
        "source": "ebay",
        "source_listing_id": str(item_id),
        "title": title[:512],
        "price": Decimal(str(value)),
        "currency": currency[:3],
        "condition": item.get("condition"),
        "image_url": image_url,
        "item_url": outbound_url,
        "seller_username": seller_username,
        "marketplace": marketplace,
        "listing_status": "active",
        "affiliate_status": affiliate_status,
        "grade": _parse_grade(title),
        "raw_metadata": item,
        "observed_at": now,
    }
