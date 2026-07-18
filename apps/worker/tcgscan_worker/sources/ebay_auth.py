"""eBay OAuth client-credentials token helper."""

from __future__ import annotations

import base64
import os
from datetime import datetime, timedelta, timezone

import httpx
import structlog

log = structlog.get_logger()

_cached_token: str | None = None
_cached_expires: datetime | None = None


async def get_ebay_oauth_token() -> str:
    """Return a valid eBay OAuth token from env or client-credentials flow."""
    global _cached_token, _cached_expires

    preset = os.getenv("EBAY_OAUTH_TOKEN", "").strip()
    if preset:
        return preset

    now = datetime.now(timezone.utc)
    if _cached_token and _cached_expires and now < _cached_expires:
        return _cached_token

    app_id = os.getenv("EBAY_APP_ID", "").strip()
    cert_id = os.getenv("EBAY_CERT_ID", "").strip()
    if not app_id or not cert_id:
        msg = "EBAY_OAUTH_TOKEN or EBAY_APP_ID+EBAY_CERT_ID required"
        log.error("ebay.auth_failed", reason="missing_credentials")
        raise ValueError(msg)

    auth = base64.b64encode(f"{app_id}:{cert_id}".encode()).decode()
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            "https://api.ebay.com/identity/v1/oauth2/token",
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
        payload = resp.json()

    token = str(payload.get("access_token", ""))
    if not token:
        msg = "eBay OAuth response missing access_token"
        log.error("ebay.auth_failed", reason="missing_access_token")
        raise ValueError(msg)

    expires_in = int(payload.get("expires_in", 7200))
    _cached_token = token
    _cached_expires = now + timedelta(seconds=max(expires_in - 60, 60))
    log.info("ebay.oauth.minted", expires_in=expires_in)
    return token
