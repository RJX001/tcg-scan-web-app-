"""Market explorer ('ladder') — ranked movers, composite indexes, populations."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from tcgscan_api.repositories.market import MarketRepo, PopulationRepo
from tcgscan_api.repositories.marketplace_listings import MarketplaceListingsRepo
from tcgscan_api.services.cards import CardOut, _to_out

SORT_OPTIONS = ("change", "change_asc", "price", "volume", "recent", "pop", "market_cap")
PRO_SORTS = ("pop",)
BROWSE_SORT_OPTIONS = ("recent", "price_asc", "price_desc")


class MoverOut(BaseModel):
    card: CardOut
    sales_count: int
    avg_usd: float | None = None
    change_pct: float | None = None
    last_sold_usd: float | None = None
    last_sold_at: str | None = None
    last_sold_grade: str | None = None
    pop_count: int | None = None


class IndexPoint(BaseModel):
    day: str
    index_value: float
    constituents: int


class MarketIndexOut(BaseModel):
    name: str
    days: int
    change_pct: float | None = None
    points: list[IndexPoint]


class PopulationEntry(BaseModel):
    grade_company: str
    grade: str
    pop_count: int
    as_of: str


class PopulationOut(BaseModel):
    total: int
    entries: list[PopulationEntry]


class ShopListingOut(BaseModel):
    card: CardOut | None = None
    title: str | None = None
    image_url: str | None = None
    source: str
    price: float
    currency: str
    price_usd: float | None = None
    grade: str | None = None
    listing_url: str | None = None
    listed_at: str


class SaleBrowseOut(BaseModel):
    card: CardOut
    source: str
    price: float
    currency: str
    price_usd: float | None = None
    grade: str | None = None
    listing_url: str | None = None
    sold_at: str
    market_region: str


class IndexSummaryOut(BaseModel):
    key: str
    name: str
    change_pct: float | None = None
    latest_value: float | None = None
    constituents: int


class FxOut(BaseModel):
    base: str = "USD"
    as_of: str | None = None
    # currency -> value of 1 unit in USD (e.g. GBP: 1.27)
    rates: dict[str, float]


async def get_movers(
    session: AsyncSession,
    *,
    days: int = 30,
    game: str | None = None,
    q: str | None = None,
    grade: str | None = None,
    sort: str = "change",
    limit: int = 20,
    offset: int = 0,
) -> list[MoverOut]:
    if sort not in SORT_OPTIONS:
        sort = "change"
    rows = await MarketRepo(session).movers(
        days=days, game=game, q=q, grade=grade, sort=sort, limit=limit, offset=offset
    )
    return [
        MoverOut(
            card=_to_out(r.card),
            sales_count=r.sales_count,
            avg_usd=r.avg_usd,
            change_pct=r.change_pct,
            last_sold_usd=r.last_sold_usd,
            last_sold_at=r.last_sold_at.isoformat() if r.last_sold_at else None,
            last_sold_grade=r.last_sold_grade,
            pop_count=r.pop_count,
        )
        for r in rows
    ]


async def get_shop_listings(
    session: AsyncSession,
    *,
    game: str | None = None,
    q: str | None = None,
    source: str | None = None,
    grade: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    listed_after: datetime | None = None,
    listed_before: datetime | None = None,
    sort: str = "recent",
    limit: int = 24,
    offset: int = 0,
) -> list[ShopListingOut]:
    if sort not in BROWSE_SORT_OPTIONS:
        sort = "recent"
    rows = await MarketplaceListingsRepo(session).browse(
        q=q,
        source=source,
        grade=grade,
        min_price=min_price,
        max_price=max_price,
        listed_after=listed_after,
        listed_before=listed_before,
        sort=sort,
        limit=limit,
        offset=offset,
    )
    out: list[ShopListingOut] = []
    for listing in rows:
        card_out: CardOut | None = None
        if listing.card_id is not None:
            from tcgscan_api.repositories.cards import CardsRepo

            card = await CardsRepo(session).get(listing.card_id)
            if card is not None:
                if game and card.game.value != game:
                    continue
                card_out = _to_out(card)
        elif game:
            continue
        price_usd = float(listing.price) if listing.currency == "USD" else None
        out.append(
            ShopListingOut(
                card=card_out,
                title=listing.title,
                image_url=listing.image_url,
                source=listing.source,
                price=float(listing.price),
                currency=listing.currency,
                price_usd=price_usd,
                grade=listing.grade,
                listing_url=listing.item_url,
                listed_at=listing.observed_at.isoformat(),
            )
        )
    return out


async def get_sales_browse(
    session: AsyncSession,
    *,
    game: str | None = None,
    q: str | None = None,
    source: str | None = None,
    grade: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    sold_after: datetime | None = None,
    sold_before: datetime | None = None,
    sort: str = "recent",
    limit: int = 24,
    offset: int = 0,
) -> list[SaleBrowseOut]:
    from tcgscan_api.services.market_region import infer_market_region

    if sort not in BROWSE_SORT_OPTIONS:
        sort = "recent"
    rows = await MarketRepo(session).browse_sales(
        game=game,
        q=q,
        source=source,
        grade=grade,
        min_price=min_price,
        max_price=max_price,
        sold_after=sold_after,
        sold_before=sold_before,
        sort=sort,
        limit=limit,
        offset=offset,
    )
    return [
        SaleBrowseOut(
            card=_to_out(r.card),
            source=r.source,
            price=r.price,
            currency=r.currency,
            price_usd=r.price_usd,
            grade=r.grade,
            listing_url=r.listing_url,
            sold_at=r.sold_at.isoformat(),
            market_region=infer_market_region(source=r.source, currency=r.currency),
        )
        for r in rows
    ]


_INDEX_NAMES = {
    None: "TCG Scan Market Index",
    "pokemon": "Pokemon Index",
    "mtg": "Magic Index",
    "yugioh": "Yu-Gi-Oh! Index",
    "lorcana": "Lorcana Index",
    "one_piece": "One Piece Index",
}


async def get_market_index(
    session: AsyncSession,
    *,
    game: str | None = None,
    days: int = 90,
) -> MarketIndexOut:
    """Equal-weighted composite: each card's daily median rebased to 100 at its
    first observation in the window, then averaged across constituents per day
    (carrying forward the latest value for cards without a sale that day)."""
    rows = await MarketRepo(session).daily_rollups(days=days, game=game)
    name = _INDEX_NAMES.get(game, f"{game} Index" if game else "TCG Scan Market Index")
    if not rows:
        return MarketIndexOut(name=name, days=days, points=[])

    by_card: dict[uuid.UUID, dict[str, float]] = {}
    all_days: set[str] = set()
    for r in rows:
        day = r.day.date().isoformat()
        by_card.setdefault(r.card_id, {})[day] = r.median_usd
        all_days.add(day)

    base: dict[uuid.UUID, float] = {}
    for card_id, series in by_card.items():
        first_day = min(series.keys())
        if series[first_day] > 0:
            base[card_id] = series[first_day]

    latest: dict[uuid.UUID, float] = {}
    points: list[IndexPoint] = []
    for day in sorted(all_days):
        for card_id, series in by_card.items():
            if card_id in base and day in series:
                latest[card_id] = series[day] / base[card_id] * 100.0
        if latest:
            points.append(
                IndexPoint(
                    day=day,
                    index_value=round(sum(latest.values()) / len(latest), 2),
                    constituents=len(latest),
                )
            )

    change_pct: float | None = None
    if len(points) >= 2 and points[0].index_value > 0:
        change_pct = round(
            (points[-1].index_value - points[0].index_value) / points[0].index_value * 100, 2
        )
    return MarketIndexOut(name=name, days=days, change_pct=change_pct, points=points)


async def get_fx_rates(session: AsyncSession) -> FxOut:
    from tcgscan_api.repositories.fx import FxRepo

    as_of, rates = await FxRepo(session).latest_rates()
    return FxOut(as_of=as_of.isoformat() if as_of else None, rates=rates)


async def get_indexes_summary(session: AsyncSession, *, days: int = 7) -> list[IndexSummaryOut]:
    """All composite indexes with their % change over the window (Indexes tab)."""
    out: list[IndexSummaryOut] = []
    for game in _INDEX_NAMES:
        idx = await get_market_index(session, game=game, days=days)
        if not idx.points:
            continue
        out.append(
            IndexSummaryOut(
                key=game or "all",
                name=idx.name,
                change_pct=idx.change_pct,
                latest_value=idx.points[-1].index_value,
                constituents=idx.points[-1].constituents,
            )
        )
    out.sort(
        key=lambda s: s.change_pct if s.change_pct is not None else float("-inf"), reverse=True
    )
    return out


async def get_population(session: AsyncSession, card_id: uuid.UUID) -> PopulationOut:
    rows = await PopulationRepo(session).for_card(card_id)
    entries = [
        PopulationEntry(
            grade_company=r.grade_company,
            grade=r.grade,
            pop_count=r.pop_count,
            as_of=r.as_of.isoformat(),
        )
        for r in rows
    ]
    return PopulationOut(total=sum(e.pop_count for e in entries), entries=entries)
