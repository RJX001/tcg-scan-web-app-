from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from tcgscan_api.db.session import get_session
from tcgscan_api.errors import NotFoundError
from tcgscan_api.services.auth_ctx import resolve_db_user
from tcgscan_api.services.watchlist import (
    WatchlistAddIn,
    WatchlistItemOut,
    add_watchlist_item,
    list_watchlist,
    remove_watchlist_item,
)

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.get("", response_model=list[WatchlistItemOut])
async def get_watchlist(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> list[WatchlistItemOut]:
    auth = await resolve_db_user(session, request)
    return await list_watchlist(session, auth)


@router.post("", response_model=WatchlistItemOut, status_code=201)
async def post_watchlist(
    body: WatchlistAddIn,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> WatchlistItemOut:
    auth = await resolve_db_user(session, request)
    try:
        return await add_watchlist_item(session, auth, body)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc


@router.delete("/{item_id}", status_code=204)
async def delete_watchlist(
    item_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> None:
    auth = await resolve_db_user(session, request)
    try:
        await remove_watchlist_item(session, auth, item_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
