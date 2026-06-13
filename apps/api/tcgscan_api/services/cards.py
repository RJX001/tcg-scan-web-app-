from __future__ import annotations

import uuid

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from tcgscan_api.db.models import CardIdentity
from tcgscan_api.errors import NotFoundError
from tcgscan_api.repositories.cards import CardsRepo
from tcgscan_api.repositories.sales import SalesRepo
from tcgscan_api.services.market_region import infer_market_region
from tcgscan_api.services.slug import card_slug_from_identity


class CardOut(BaseModel):
    id: str
    slug: str
    game: str
    name: str
    set_code: str | None = None
    set_name: str | None = None
    number: str | None = None
    rarity: str | None = None
    image_urls: dict[str, object] | None = None


class CompOut(BaseModel):
    source: str
    kind: str
    sold_at: str
    price: float
    currency: str
    grade: str | None = None
    listing_url: str | None = None
    market_region: str


class ListingOut(BaseModel):
    source: str
    price: float
    currency: str
    grade: str | None = None
    listing_url: str | None = None
    listed_at: str
    market_region: str


class CompSummary(BaseModel):
    count: int
    mean_usd: float | None = None
    median_usd: float | None = None
    min_usd: float | None = None
    max_usd: float | None = None


class CompSummaryByGrade(BaseModel):
    raw: CompSummary
    graded: CompSummary


class ChartPoint(BaseModel):
    day: str
    median_usd: float
    sample_count: int


class MarketplacePriceOut(BaseModel):
    source: str
    label: str
    avg_usd: float | None = None
    sample_count: int = 0
    search_url: str


class SourcePrices(BaseModel):
    days: int = 30
    ebay_median_usd: float | None = None
    tcgplayer_median_usd: float | None = None
    cardmarket_median_usd: float | None = None
    marketplaces: list[MarketplacePriceOut] = []


def _to_out(card: CardIdentity) -> CardOut:
    return CardOut(
        id=str(card.id),
        slug=card_slug_from_identity(card),
        game=str(card.game.value if hasattr(card.game, "value") else card.game),
        name=card.name,
        set_code=card.set_code,
        set_name=card.set_name,
        number=card.number,
        rarity=card.rarity,
        image_urls=card.image_urls,
    )


async def get_card(session: AsyncSession, card_id: uuid.UUID) -> CardOut:
    card = await CardsRepo(session).get(card_id)
    if card is None:
        raise NotFoundError(f"card not found: {card_id}")
    return _to_out(card)


async def get_card_by_slug(session: AsyncSession, slug: str) -> CardOut:
    card = await CardsRepo(session).get_by_slug(slug)
    if card is None:
        raise NotFoundError(f"card not found: {slug}")
    return _to_out(card)


async def get_comps(
    session: AsyncSession,
    card_id: uuid.UUID,
    days: int = 30,
    *,
    source: str | None = None,
    grade: str | None = None,
) -> list[CompOut]:
    rows = await SalesRepo(session).comps_for_card(card_id, days=days, source=source, grade=grade)
    return [
        CompOut(
            source=r.source,
            kind=str(r.kind.value if hasattr(r.kind, "value") else r.kind),
            sold_at=r.sold_at.isoformat(),
            price=float(r.price),
            currency=r.currency,
            grade=r.grade,
            listing_url=r.listing_url,
            market_region=infer_market_region(
                source=r.source, currency=r.currency, listing_url=r.listing_url
            ),
        )
        for r in rows
    ]


async def get_comp_summary(
    session: AsyncSession, card_id: uuid.UUID, days: int = 30
) -> CompSummary:
    rows = await SalesRepo(session).comps_for_card(card_id, days=days)
    prices = [
        float(r.price_usd or r.price)
        for r in rows
        if r.price_usd is not None or r.currency == "USD"
    ]
    if not prices:
        return CompSummary(count=0)
    prices_sorted = sorted(prices)
    mid = len(prices_sorted) // 2
    median = (
        prices_sorted[mid]
        if len(prices_sorted) % 2
        else (prices_sorted[mid - 1] + prices_sorted[mid]) / 2
    )
    return CompSummary(
        count=len(prices),
        mean_usd=sum(prices) / len(prices),
        median_usd=median,
        min_usd=min(prices),
        max_usd=max(prices),
    )


async def search_cards(
    session: AsyncSession, *, q: str, game: str | None = None, limit: int = 20
) -> list[CardOut]:
    if not q.strip():
        return []
    rows = await CardsRepo(session).search(q=q, game=game, limit=limit)
    return [_to_out(c) for c in rows]


async def get_chart(
    session: AsyncSession, card_id: uuid.UUID, *, days: int = 90, grade_bucket: str = "raw"
) -> list[ChartPoint]:
    rows = await SalesRepo(session).chart_series(card_id, days=days, grade_bucket=grade_bucket)
    if rows:
        return [
            ChartPoint(
                day=r.day.date().isoformat(),
                median_usd=float(r.median_usd),
                sample_count=r.sample_count,
            )
            for r in rows
        ]
    # Fallback: aggregate comps by day when rollups not yet computed
    comp_rows = await SalesRepo(session).comps_for_card(card_id, days=days)
    by_day: dict[str, list[float]] = {}
    for r in comp_rows:
        day_key = r.sold_at.date().isoformat()
        price = float(r.price_usd or r.price)
        by_day.setdefault(day_key, []).append(price)
    points: list[ChartPoint] = []
    for day in sorted(by_day.keys()):
        prices = by_day[day]
        prices.sort()
        mid = prices[len(prices) // 2]
        points.append(ChartPoint(day=day, median_usd=mid, sample_count=len(prices)))
    return points


async def get_source_prices(
    session: AsyncSession, card_id: uuid.UUID, days: int = 30
) -> SourcePrices:
    from tcgscan_api.services.marketplace_search import marketplace_search_urls

    card = await CardsRepo(session).get(card_id)
    if card is None:
        raise NotFoundError(f"card not found: {card_id}")
    card_out = _to_out(card)
    summary = await SalesRepo(session).source_summary(card_id, days=days)
    urls = marketplace_search_urls(card_out)

    tiles: list[MarketplacePriceOut] = []
    for source, label in (
        ("ebay", "eBay"),
        ("tcgplayer", "TCGPlayer"),
        ("cardmarket", "Cardmarket"),
    ):
        stats = summary.get(source)
        avg_usd = stats[0] if stats else None
        count = stats[1] if stats else 0
        tiles.append(
            MarketplacePriceOut(
                source=source,
                label=label,
                avg_usd=avg_usd,
                sample_count=count,
                search_url=urls[source],
            )
        )

    return SourcePrices(
        days=days,
        ebay_median_usd=summary.get("ebay", (None, 0))[0],
        tcgplayer_median_usd=summary.get("tcgplayer", (None, 0))[0],
        cardmarket_median_usd=summary.get("cardmarket", (None, 0))[0],
        marketplaces=tiles,
    )


async def get_listings(
    session: AsyncSession,
    card_id: uuid.UUID,
    *,
    limit: int = 20,
    source: str | None = None,
    grade: str | None = None,
) -> list[ListingOut]:
    rows = await SalesRepo(session).listings_for_card(
        card_id, limit=limit, source=source, grade=grade
    )
    return [
        ListingOut(
            source=r.source,
            price=float(r.price),
            currency=r.currency,
            grade=r.grade,
            listing_url=r.listing_url,
            listed_at=r.sold_at.isoformat(),
            market_region=infer_market_region(
                source=r.source, currency=r.currency, listing_url=r.listing_url
            ),
        )
        for r in rows
    ]


def _summary_from_prices(prices: list[float]) -> CompSummary:
    if not prices:
        return CompSummary(count=0)
    prices_sorted = sorted(prices)
    mid = len(prices_sorted) // 2
    median = (
        prices_sorted[mid]
        if len(prices_sorted) % 2
        else (prices_sorted[mid - 1] + prices_sorted[mid]) / 2
    )
    return CompSummary(
        count=len(prices),
        mean_usd=sum(prices) / len(prices),
        median_usd=median,
        min_usd=min(prices),
        max_usd=max(prices),
    )


async def get_comp_summary_by_grade(
    session: AsyncSession, card_id: uuid.UUID, days: int = 30
) -> CompSummaryByGrade:
    rows = await SalesRepo(session).comps_for_card(card_id, days=days)
    raw_prices: list[float] = []
    graded_prices: list[float] = []
    for r in rows:
        if r.price_usd is None and r.currency != "USD":
            continue
        price = float(r.price_usd or r.price)
        grade = (r.grade or "raw").lower()
        if grade in ("raw", "none", ""):
            raw_prices.append(price)
        else:
            graded_prices.append(price)
    return CompSummaryByGrade(
        raw=_summary_from_prices(raw_prices),
        graded=_summary_from_prices(graded_prices),
    )
