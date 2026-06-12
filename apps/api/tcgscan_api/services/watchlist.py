"""Watchlist — track cards without owning them. Pro feature (Card Ladder parity)."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from tcgscan_api.errors import NotFoundError
from tcgscan_api.middleware.auth import AuthUser
from tcgscan_api.repositories.cards import CardsRepo
from tcgscan_api.repositories.users import WatchlistRepo
from tcgscan_api.services.cards import CardOut, _to_out, get_comp_summary
from tcgscan_api.services.tier import require_pro


class WatchlistAddIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    card_id: uuid.UUID


class WatchlistItemOut(BaseModel):
    id: str
    card: CardOut
    median_usd_30d: float | None = None
    created_at: str


async def list_watchlist(session: AsyncSession, user: AuthUser) -> list[WatchlistItemOut]:
    rows = await WatchlistRepo(session).list_for_user(user.id)
    cards_repo = CardsRepo(session)
    out: list[WatchlistItemOut] = []
    for row in rows:
        card = await cards_repo.get(row.card_id)
        if card is None:
            continue
        summary = await get_comp_summary(session, row.card_id, days=30)
        out.append(
            WatchlistItemOut(
                id=str(row.id),
                card=_to_out(card),
                median_usd_30d=summary.median_usd,
                created_at=row.created_at.isoformat(),
            )
        )
    return out


async def add_watchlist_item(
    session: AsyncSession, user: AuthUser, body: WatchlistAddIn
) -> WatchlistItemOut:
    require_pro(user, feature="Watchlist")
    card = await CardsRepo(session).get(body.card_id)
    if card is None:
        raise NotFoundError(f"card not found: {body.card_id}")
    row = await WatchlistRepo(session).add(user_id=user.id, card_id=body.card_id)
    summary = await get_comp_summary(session, body.card_id, days=30)
    return WatchlistItemOut(
        id=str(row.id),
        card=_to_out(card),
        median_usd_30d=summary.median_usd,
        created_at=row.created_at.isoformat(),
    )


async def remove_watchlist_item(session: AsyncSession, user: AuthUser, item_id: uuid.UUID) -> None:
    removed = await WatchlistRepo(session).remove(user.id, item_id)
    if not removed:
        raise NotFoundError(f"watchlist item not found: {item_id}")
