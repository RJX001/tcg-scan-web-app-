"""eBay Browse API client for active listing search (API-side ingest)."""

from __future__ import annotations

import base64
import os
from typing import Any

import httpx
import structlog

from tcgscan_api.config import get_settings

log = structlog.get_logger()

BROWSE_SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"
OAUTH_URL = "https://api.ebay.com/identity/v1/oauth2/token"


def ebay_configured() -> bool:
    settings = get_settings()
    return bool(settings.ebay_oauth_token) or (
        bool(settings.ebay_app_id) and bool(settings.ebay_cert_id)
    )


async def get_ebay_access_token() -> str:
    settings = get_settings()
    if settings.ebay_oauth_token:
        return settings.ebay_oauth_token.strip()
    app_id = (settings.ebay_app_id or "").strip()
    cert_id = (settings.ebay_cert_id or "").strip()
    if not app_id or not cert_id:
        raise RuntimeError("eBay credentials not configured")
    auth = base64.b64encode(f"{app_id}:{cert_id}".encode()).decode()
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(
            OAUTH_URL,
            headers={
                "Authorization": f"Basic {auth}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "client_credentials",
                "scope": "https://api.ebay.com/oauth/api_scope",
            },
        )
        resp.raise_for_status()
        token = str(resp.json().get("access_token", ""))
    if not token:
        raise RuntimeError("OAuth succeeded but access_token missing")
    return token


async def search_item_summaries(
    *,
    query: str,
    limit: int = 25,
    marketplace_id: str | None = None,
) -> list[dict[str, Any]]:
    """Search eBay Browse API item summaries."""
    settings = get_settings()
    marketplace = marketplace_id or settings.ebay_marketplace_id or "EBAY_GB"
    token = await get_ebay_access_token()
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            BROWSE_SEARCH_URL,
            params={"q": query, "limit": min(limit, 100)},
            headers={
                "Authorization": f"Bearer {token}",
                "X-EBAY-C-MARKETPLACE-ID": marketplace,
                "Accept": "application/json",
            },
        )
        resp.raise_for_status()
        payload = resp.json()
    items = payload.get("itemSummaries") or []
    if not isinstance(items, list):
        return []
    return [it for it in items if isinstance(it, dict)]
