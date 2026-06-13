from __future__ import annotations

import base64
import binascii

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from tcgscan_api.config import get_settings
from tcgscan_api.middleware.rate_limit import check_scan_rate_limit
from tcgscan_api.services.scan import ScanInput, ScanResult, run_scan

router = APIRouter(prefix="/scan", tags=["scan"])


@router.post("", response_model=ScanResult)
async def scan(
    request: Request,
    image: UploadFile = File(...),
    game: str | None = Form(default=None),
    top_k: int = Form(default=5),
) -> ScanResult:
    settings = get_settings()
    if settings.environment == "production" and not settings.modal_embed_url:
        raise HTTPException(
            status_code=503,
            detail="Card scan is in beta. Use Search to find cards.",
        )
    await check_scan_rate_limit(request)
    raw = await image.read()
    if not raw:
        raise HTTPException(status_code=400, detail="empty image")
    try:
        b64 = base64.b64encode(raw).decode("ascii")
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=400, detail="invalid image bytes") from exc
    return await run_scan(ScanInput(image_b64=b64, game_hint=game, top_k=top_k))
