from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from tcgscan_api.db.session import get_session
from tcgscan_api.services.auth_ctx import resolve_db_user
from tcgscan_api.services.cache import cache_get, cache_set
from tcgscan_api.services.market import (
    PRO_SORTS,
    FxOut,
    IndexSummaryOut,
    MarketIndexOut,
    MoverOut,
    SaleBrowseOut,
    ShopListingOut,
    get_fx_rates,
    get_indexes_summary,
    get_market_index,
    get_movers,
    get_sales_browse,
    get_shop_listings,
)
from tcgscan_api.services.tier import require_pro

router = APIRouter(prefix="/market", tags=["market"])


def _parse_dt(value: str | None, *, name: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid {name}: use ISO-8601") from exc


@router.get("/movers", response_model=list[MoverOut])
async def market_movers(
    request: Request,
    days: int = Query(default=30, ge=7, le=365),
    game: str | None = None,
    q: str | None = Query(default=None, max_length=100),
    grade: str | None = Query(default=None, max_length=16),
    sort: str = Query(default="change"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[MoverOut]:
    if sort in PRO_SORTS:
        auth = await resolve_db_user(session, request)
        require_pro(auth, feature=f"'{sort}' sort")
    key = f"market:movers:{days}:{game or ''}:{q or ''}:{grade or ''}:{sort}:{limit}:{offset}"
    cached = await cache_get(key)
    if cached is not None:
        return [MoverOut.model_validate(item) for item in cached]
    out = await get_movers(
        session, days=days, game=game, q=q, grade=grade, sort=sort, limit=limit, offset=offset
    )
    await cache_set(key, [m.model_dump(mode="json") for m in out], ttl_s=300)
    return out


@router.get("/listings", response_model=list[ShopListingOut])
async def market_listings(
    game: str | None = None,
    q: str | None = Query(default=None, max_length=100),
    source: str | None = None,
    grade: str | None = None,
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    listed_after: str | None = Query(default=None, description="ISO date — listings on/after"),
    listed_before: str | None = Query(default=None, description="ISO date — listings on/before"),
    sort: str = Query(default="recent"),
    limit: int = Query(default=24, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[ShopListingOut]:
    after = _parse_dt(listed_after, name="listed_after")
    before = _parse_dt(listed_before, name="listed_before")
    key = (
        f"market:listings:{game or ''}:{q or ''}:{source or ''}:{grade or ''}"
        f":{min_price or ''}:{max_price or ''}:{listed_after or ''}:{listed_before or ''}"
        f":{sort}:{limit}:{offset}"
    )
    cached = await cache_get(key)
    if cached is not None:
        return [ShopListingOut.model_validate(item) for item in cached]
    out = await get_shop_listings(
        session,
        game=game,
        q=q,
        source=source,
        grade=grade,
        min_price=min_price,
        max_price=max_price,
        listed_after=after,
        listed_before=before,
        sort=sort,
        limit=limit,
        offset=offset,
    )
    await cache_set(key, [m.model_dump(mode="json") for m in out], ttl_s=300)
    return out


@router.get("/sales", response_model=list[SaleBrowseOut])
async def market_sales(
    game: str | None = None,
    q: str | None = Query(default=None, max_length=100),
    source: str | None = None,
    grade: str | None = None,
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    sold_after: str | None = Query(default=None, description="ISO date — sold on/after"),
    sold_before: str | None = Query(default=None, description="ISO date — sold on/before"),
    sort: str = Query(default="recent"),
    limit: int = Query(default=24, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[SaleBrowseOut]:
    after = _parse_dt(sold_after, name="sold_after")
    before = _parse_dt(sold_before, name="sold_before")
    key = (
        f"market:sales:{game or ''}:{q or ''}:{source or ''}:{grade or ''}"
        f":{min_price or ''}:{max_price or ''}:{sold_after or ''}:{sold_before or ''}"
        f":{sort}:{limit}:{offset}"
    )
    cached = await cache_get(key)
    if cached is not None:
        return [SaleBrowseOut.model_validate(item) for item in cached]
    out = await get_sales_browse(
        session,
        game=game,
        q=q,
        source=source,
        grade=grade,
        min_price=min_price,
        max_price=max_price,
        sold_after=after,
        sold_before=before,
        sort=sort,
        limit=limit,
        offset=offset,
    )
    await cache_set(key, [m.model_dump(mode="json") for m in out], ttl_s=300)
    return out


@router.get("/indexes", response_model=list[IndexSummaryOut])
async def market_indexes(
    days: int = Query(default=7, ge=7, le=365),
    session: AsyncSession = Depends(get_session),
) -> list[IndexSummaryOut]:
    key = f"market:indexes:{days}"
    cached = await cache_get(key)
    if cached is not None:
        return [IndexSummaryOut.model_validate(item) for item in cached]
    out = await get_indexes_summary(session, days=days)
    await cache_set(key, [m.model_dump(mode="json") for m in out], ttl_s=900)
    return out


@router.get("/fx", response_model=FxOut)
async def market_fx(session: AsyncSession = Depends(get_session)) -> FxOut:
    key = "market:fx"
    cached = await cache_get(key)
    if cached is not None:
        return FxOut.model_validate(cached)
    out = await get_fx_rates(session)
    await cache_set(key, out.model_dump(mode="json"), ttl_s=3600)
    return out


@router.get("/index", response_model=MarketIndexOut)
async def market_index(
    days: int = Query(default=90, ge=7, le=365),
    game: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> MarketIndexOut:
    key = f"market:index:{days}:{game or ''}"
    cached = await cache_get(key)
    if cached is not None:
        return MarketIndexOut.model_validate(cached)
    out = await get_market_index(session, game=game, days=days)
    await cache_set(key, out.model_dump(mode="json"), ttl_s=900)
    return out
