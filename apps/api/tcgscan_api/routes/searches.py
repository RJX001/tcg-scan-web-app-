from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from tcgscan_api.db.session import get_session
from tcgscan_api.errors import NotFoundError
from tcgscan_api.services.auth_ctx import resolve_db_user
from tcgscan_api.services.saved_searches import (
    SavedSearchCreateIn,
    SavedSearchOut,
    create_saved_search,
    delete_saved_search,
    list_saved_searches,
)

router = APIRouter(prefix="/searches", tags=["searches"])


@router.get("", response_model=list[SavedSearchOut])
async def get_searches(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> list[SavedSearchOut]:
    auth = await resolve_db_user(session, request)
    return await list_saved_searches(session, auth)


@router.post("", response_model=SavedSearchOut, status_code=201)
async def post_search(
    body: SavedSearchCreateIn,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> SavedSearchOut:
    auth = await resolve_db_user(session, request)
    return await create_saved_search(session, auth, body)


@router.delete("/{search_id}", status_code=204)
async def delete_search(
    search_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> None:
    auth = await resolve_db_user(session, request)
    try:
        await delete_saved_search(session, auth, search_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
