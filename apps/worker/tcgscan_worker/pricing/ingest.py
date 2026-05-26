"""Ingest sold comps / active listings for cards into sale_event."""

from __future__ import annotations

import argparse
import asyncio
import uuid
from decimal import Decimal

import structlog
from sqlalchemy import select

from tcgscan_api.db.models import CardIdentity, Game, SaleKind
from tcgscan_api.repositories.cards import CardsRepo
from tcgscan_api.repositories.sales import SalesRepo
from tcgscan_worker.db_bridge import card_session
from tcgscan_worker.pricing.fx import ensure_fx_rates, to_usd
from tcgscan_worker.sources.registry import get_source

log = structlog.get_logger()

DEFAULT_SOURCES = ["ebay_sold", "ebay_active", "tcgplayer", "cardmarket"]


def _market_query(name: str, set_name: str | None, game: str) -> str:
    parts = [name]
    if set_name:
        parts.append(set_name)
    if game.startswith("sports_"):
        parts.append(game.replace("sports_", "").replace("_", " "))
        parts.append("card")
    elif game == "pokemon":
        parts.append("pokemon tcg")
    return " ".join(parts)


async def ingest_for_card(
    card_id: uuid.UUID,
    *,
    sources: list[str] | None = None,
    limit: int = 50,
) -> int:
    """Fetch comps from registered sources and persist to sale_event."""
    source_ids = sources or DEFAULT_SOURCES
    async with card_session() as session:
        await ensure_fx_rates(session)
        card = await CardsRepo(session).get(card_id)
        if card is None:
            msg = f"card not found: {card_id}"
            raise ValueError(msg)

        game = card.game.value if isinstance(card.game, Game) else str(card.game)
        query = _market_query(card.name, card.set_name, game)
        rows: list[dict[str, object]] = []

        for source_id in source_ids:
            src = get_source(source_id)
            async for record in src.iter_records(query=query, limit=limit):
                record.card_id = card_id
                row = record.to_row()
                row["card_id"] = card_id
                row["kind"] = SaleKind(row["kind"])
                if row.get("price_usd") is None:
                    row["price_usd"] = await to_usd(
                        session,
                        amount=Decimal(str(row["price"])),
                        currency=str(row["currency"]),
                    )
                rows.append(row)

            await src.client.aclose()

        if not rows:
            log.warning("pricing.ingest.empty", card_id=str(card_id), query=query)
            return 0

        written = await SalesRepo(session).bulk_insert(rows)
        log.info("pricing.ingest.done", card_id=str(card_id), rows=written, query=query)
        return written


async def ingest_batch(
    *,
    game: str | None = None,
    card_limit: int = 1000,
    per_source_limit: int = 25,
    sources: list[str] | None = None,
) -> int:
    """Batch ingest pricing for top N cards (optionally filtered by game slug)."""
    source_ids = sources or DEFAULT_SOURCES
    total = 0
    async with card_session() as session:
        stmt = select(CardIdentity).order_by(CardIdentity.name).limit(card_limit)
        if game:
            if game == "sports":
                stmt = stmt.where(
                    CardIdentity.game.in_(
                        [
                            Game.sports_baseball,
                            Game.sports_basketball,
                            Game.sports_football,
                            Game.sports_soccer,
                        ]
                    )
                )
            else:
                stmt = stmt.where(CardIdentity.game == Game(game))
        cards = list((await session.execute(stmt)).scalars().all())

    for card in cards:
        try:
            total += await ingest_for_card(
                card.id, sources=source_ids, limit=per_source_limit
            )
        except Exception as exc:
            log.warning("pricing.batch.card_failed", card_id=str(card.id), error=str(exc))
    log.info("pricing.batch.done", cards=len(cards), rows=total, game=game)
    return total


async def ingest_all_pokemon(*, limit_per_card: int = 20, card_limit: int = 10) -> int:
    return await ingest_batch(
        game="pokemon",
        card_limit=card_limit,
        per_source_limit=limit_per_card,
        sources=["ebay_sold"],
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest marketplace comps")
    parser.add_argument("--card-id", type=uuid.UUID, help="Target card UUID")
    parser.add_argument("--source", action="append", dest="sources", help="Source id(s)")
    parser.add_argument("--limit", type=int, default=50, help="Per-source record limit")
    parser.add_argument("--game", type=str, default=None, help="Batch by game slug")
    parser.add_argument("--card-limit", type=int, default=1000, help="Batch card count")
    parser.add_argument(
        "--all-pokemon",
        action="store_true",
        help="Batch ingest first 10 Pokemon cards (dev)",
    )
    args = parser.parse_args(argv)

    if args.all_pokemon:
        n = asyncio.run(ingest_all_pokemon())
        print(f"ingested {n} sale events across pokemon batch")
        return 0

    if args.game:
        sources = args.sources or DEFAULT_SOURCES
        n = asyncio.run(
            ingest_batch(
                game=args.game,
                card_limit=args.card_limit,
                per_source_limit=args.limit,
                sources=sources,
            )
        )
        print(f"ingested {n} sale events for game={args.game}")
        return 0

    if args.card_id is None:
        parser.error("--card-id, --game, or --all-pokemon required")
        return 2

    sources = args.sources or DEFAULT_SOURCES
    n = asyncio.run(ingest_for_card(args.card_id, sources=sources, limit=args.limit))
    print(f"ingested {n} sale events for {args.card_id}")
    return 0
