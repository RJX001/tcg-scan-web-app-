from __future__ import annotations

import uuid

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from tcgscan_api.db.models import CardIdentity
from tcgscan_api.errors import NotFoundError
from tcgscan_api.repositories.cards import CardsRepo
from tcgscan_api.repositories.sales import SalesRepo
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


class CompSummary(BaseModel):
    count: int
    mean_usd: float | None = None
    median_usd: float | None = None
    min_usd: float | None = None
    max_usd: float | None = None


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


async def get_comps(session: AsyncSession, card_id: uuid.UUID, days: int = 30) -> list[CompOut]:
    rows = await SalesRepo(session).comps_for_card(card_id, days=days)
    return [
        CompOut(
            source=r.source,
            kind=str(r.kind.value if hasattr(r.kind, "value") else r.kind),
            sold_at=r.sold_at.isoformat(),
            price=float(r.price),
            currency=r.currency,
            grade=r.grade,
            listing_url=r.listing_url,
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
