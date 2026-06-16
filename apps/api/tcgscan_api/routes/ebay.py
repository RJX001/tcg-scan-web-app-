"""Public eBay compliance routes (Marketplace Account Deletion notifications)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse, Response

from tcgscan_api.services.ebay_account_deletion import (
    build_challenge_response,
    log_account_deletion_notification,
)

router = APIRouter(prefix="/ebay", tags=["ebay"])


@router.get("/account-deletion")
async def ebay_account_deletion_challenge(
    challenge_code: str | None = Query(default=None),
) -> JSONResponse:
    if not challenge_code or not challenge_code.strip():
        return JSONResponse(
            status_code=400,
            content={"detail": "challenge_code query parameter is required"},
            media_type="application/json",
        )
    status_code, body = build_challenge_response(challenge_code.strip())
    return JSONResponse(status_code=status_code, content=body, media_type="application/json")


@router.post("/account-deletion", status_code=204)
async def ebay_account_deletion_notification(request: Request) -> Response:
    try:
        body: Any = await request.json()
    except Exception:
        body = None
    log_account_deletion_notification(body)
    return Response(status_code=204)
