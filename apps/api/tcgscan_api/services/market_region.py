"""Infer marketplace region from sale/listing metadata."""

from __future__ import annotations

MarketRegion = str  # "us" | "uk" | "eu"


def infer_market_region(
    *,
    source: str,
    currency: str,
    listing_url: str | None = None,
) -> str:
    src = source.lower()
    cur = currency.upper()
    url = (listing_url or "").lower()

    if src == "tcgplayer":
        return "us"
    if src == "cardmarket":
        return "eu"
    if "ebay_uk" in src or src in ("ebayuk", "ebay-uk"):
        return "uk"
    if "ebay.co.uk" in url:
        return "uk"
    if "cardmarket." in url:
        return "eu"
    if cur == "GBP":
        return "uk"
    if cur == "EUR":
        return "eu"
    if src == "ebay" and cur == "USD":
        return "us"
    if "ebay.com" in url:
        return "us"
    if cur == "USD":
        return "us"
    return "us"
