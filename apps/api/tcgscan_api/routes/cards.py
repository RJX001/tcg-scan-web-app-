from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from tcgscan_api.db.session import get_session
from tcgscan_api.errors import NotFoundError
from tcgscan_api.services.cache import cache_get, cache_set
from tcgscan_api.services.cards import (
    CardOut,
    CompOut,
    CompSummary,
    get_card,
    get_card_by_slug,
    get_comp_summary,
    get_comps,
)

router = APIRouter(prefix="/cards", tags=["cards"])


@router.get("/slug/{slug}", response_model=CardOut)
async def card_by_slug(slug: str, session: AsyncSession = Depends(get_session)) -> CardOut:
    key = f"cards:slug:{slug}"
    cached = await cache_get(key)
    if cached:
        return CardOut.model_validate(cached)
    try:
        out = await get_card_by_slug(session, slug)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    await cache_set(key, out.model_dump(mode="json"), ttl_s=900)
    return out


@router.get("/{card_id}", response_model=CardOut)
async def card_detail(card_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> CardOut:
    key = f"cards:{card_id}"
    cached = await cache_get(key)
    if cached:
        return CardOut.model_validate(cached)
    try:
        out = await get_card(session, card_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    await cache_set(key, out.model_dump(mode="json"), ttl_s=900)
    return out


@router.get("/{card_id}/comps", response_model=list[CompOut])
async def card_comps(
    card_id: uuid.UUID,
    days: int = Query(default=30, ge=1, le=365),
    session: AsyncSession = Depends(get_session),
) -> list[CompOut]:
    return await get_comps(session, card_id, days=days)


@router.get("/{card_id}/comps/summary", response_model=CompSummary)
async def card_comps_summary(
    card_id: uuid.UUID,
    days: int = Query(default=30, ge=1, le=365),
    session: AsyncSession = Depends(get_session),
) -> CompSummary:
    return await get_comp_summary(session, card_id, days=days)
