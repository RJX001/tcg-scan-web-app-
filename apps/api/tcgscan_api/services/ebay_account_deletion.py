"""eBay Marketplace Account Deletion / Closure notification compliance."""

from __future__ import annotations

import hashlib
from typing import Any

import structlog

from tcgscan_api.config import get_settings

log = structlog.get_logger()

DEFAULT_ENDPOINT_URL = (
    "https://tcg-scan-web-app-production.up.railway.app/v1/ebay/account-deletion"
)


def account_deletion_endpoint_url() -> str:
    return get_settings().ebay_account_deletion_endpoint_url.strip()


def account_deletion_verification_token() -> str | None:
    token = get_settings().ebay_account_deletion_verification_token
    if token and token.strip():
        return token.strip()
    return None


def compute_challenge_response(challenge_code: str, verification_token: str, endpoint_url: str) -> str:
    payload = f"{challenge_code}{verification_token}{endpoint_url}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_challenge_response(challenge_code: str) -> tuple[int, dict[str, str]]:
    token = account_deletion_verification_token()
    if not token:
        return 500, {"detail": "Account deletion verification is not configured"}
    endpoint_url = account_deletion_endpoint_url()
    digest = compute_challenge_response(challenge_code, token, endpoint_url)
    return 200, {"challengeResponse": digest}


def _first_str(data: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = data.get(key)
        if value is not None and str(value).strip():
            return str(value)
    return None


def extract_notification_metadata(body: Any) -> dict[str, str | None]:
    if not isinstance(body, dict):
        return {
            "notificationId": None,
            "topic": None,
            "eventDate": None,
            "userId": None,
            "eiasToken": None,
        }

    notification = body.get("notification")
    if not isinstance(notification, dict):
        notification = body

    metadata = body.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}

    data = notification.get("data")
    if not isinstance(data, dict):
        data = notification

    return {
        "notificationId": _first_str(notification, "notificationId", "notification_id"),
        "topic": _first_str(metadata, "topic") or _first_str(notification, "topic"),
        "eventDate": _first_str(notification, "eventDate", "event_date", "publishDate"),
        "userId": _first_str(data, "userId", "user_id", "username"),
        "eiasToken": _first_str(data, "eiasToken", "eias_token"),
    }


def log_account_deletion_notification(body: Any) -> None:
    # TODO(agent): if CardChart stores eBay user/seller identifiers, delete or anonymise
    # matching records when this notification is received.
    meta = extract_notification_metadata(body)
    log.info(
        "ebay.account_deletion_notification",
        notification_id=meta["notificationId"],
        topic=meta["topic"],
        event_date=meta["eventDate"],
        user_id=meta["userId"],
        eias_token=meta["eiasToken"],
    )
