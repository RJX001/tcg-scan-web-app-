from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from tcgscan_api.db.session import get_session
from tcgscan_api.services.auth_ctx import resolve_db_user
from tcgscan_api.services.digest import DigestPreviewOut, preview_digest

router = APIRouter(tags=["insights"])


@router.get("/digest/preview", response_model=DigestPreviewOut)
async def digest_preview(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> DigestPreviewOut:
    auth = await resolve_db_user(session, request)
    return await preview_digest(session, auth)
