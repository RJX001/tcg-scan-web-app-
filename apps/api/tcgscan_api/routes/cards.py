from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from tcgscan_api.db.session import get_session
from tcgscan_api.errors import NotFoundError
from tcgscan_api.services.cache import cache_get, cache_set
from tcgscan_api.services.cards import (
    CardOut,
    ChartPoint,
    CompOut,
    CompSummary,
    CompSummaryByGrade,
    ListingOut,
    SourcePrices,
    get_card,
    get_card_by_slug,
    get_chart,
    get_comp_summary,
    get_comp_summary_by_grade,
    get_comps,
    get_listings,
    get_source_prices,
    search_cards,
)
from tcgscan_api.services.grade_roi import GradeVerdict, compute_verdict
from tcgscan_api.services.market import PopulationOut, get_population

router = APIRouter(prefix="/cards", tags=["cards"])


@router.get("/search", response_model=list[CardOut])
async def card_search(
    q: str = Query(min_length=1),
    game: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> list[CardOut]:
    return await search_cards(session, q=q, game=game, limit=limit)


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
    source: str | None = None,
    grade: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[CompOut]:
    return await get_comps(session, card_id, days=days, source=source, grade=grade)


@router.get("/{card_id}/listings", response_model=list[ListingOut])
async def card_listings(
    card_id: uuid.UUID,
    limit: int = Query(default=20, ge=1, le=100),
    source: str | None = None,
    grade: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[ListingOut]:
    return await get_listings(session, card_id, limit=limit, source=source, grade=grade)


@router.get("/{card_id}/comps/summary/by-grade", response_model=CompSummaryByGrade)
async def card_comps_summary_by_grade(
    card_id: uuid.UUID,
    days: int = Query(default=30, ge=1, le=365),
    session: AsyncSession = Depends(get_session),
) -> CompSummaryByGrade:
    return await get_comp_summary_by_grade(session, card_id, days=days)


@router.get("/{card_id}/comps/summary", response_model=CompSummary)
async def card_comps_summary(
    card_id: uuid.UUID,
    days: int = Query(default=30, ge=1, le=365),
    session: AsyncSession = Depends(get_session),
) -> CompSummary:
    return await get_comp_summary(session, card_id, days=days)


@router.get("/{card_id}/chart", response_model=list[ChartPoint])
async def card_chart(
    card_id: uuid.UUID,
    days: int = Query(default=90, ge=7, le=365),
    grade_bucket: str = Query(default="raw"),
    session: AsyncSession = Depends(get_session),
) -> list[ChartPoint]:
    return await get_chart(session, card_id, days=days, grade_bucket=grade_bucket)


@router.get("/{card_id}/sources", response_model=SourcePrices)
async def card_source_prices(
    card_id: uuid.UUID,
    days: int = Query(default=30, ge=1, le=365),
    session: AsyncSession = Depends(get_session),
) -> SourcePrices:
    return await get_source_prices(session, card_id, days=days)


@router.get("/{card_id}/population", response_model=PopulationOut)
async def card_population(
    card_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> PopulationOut:
    return await get_population(session, card_id)


@router.get("/{card_id}/grade-roi", response_model=GradeVerdict)
async def card_grade_roi(
    card_id: uuid.UUID,
    psa_high: int = Query(default=9, ge=1, le=10),
    session: AsyncSession = Depends(get_session),
) -> GradeVerdict:
    verdict = await compute_verdict(session, card_id, psa_high=psa_high)
    if verdict is None:
        raise HTTPException(status_code=404, detail="Not enough comps for ROI estimate")
    return verdict
