"""Thin DB bridge — re-exports the API's repositories so worker doesn't duplicate ORM."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession

from tcgscan_api.db.session import get_sessionmaker
from tcgscan_api.repositories.cards import CardsRepo


@asynccontextmanager
async def card_session() -> AsyncIterator[AsyncSession]:
    async with get_sessionmaker()() as session:
        yield session


async def upsert_cards(session: AsyncSession, rows: list[dict[str, object]]) -> int:
    written: int = await CardsRepo(session).upsert_many(rows)
    return written
