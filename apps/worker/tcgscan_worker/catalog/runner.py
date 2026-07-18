from __future__ import annotations

import asyncio
from typing import Any

import structlog

# Side-effect imports to populate REGISTRY.
from tcgscan_worker.catalog import lorcana, mtg, one_piece, pokemon, sports, yugioh  # noqa: F401
from tcgscan_worker.catalog.base import REGISTRY
from tcgscan_worker.db_bridge import card_session, upsert_cards

log = structlog.get_logger()


async def ingest_game(game: str, *, limit: int | None = None, batch_size: int = 500) -> int:
    cls = REGISTRY.get(game)
    if cls is None:
        known = sorted(REGISTRY)
        log.error("catalog.unknown_game", game=game, known=known)
        raise ValueError(f"unknown game: {game}. Known: {known}")
    ingester = cls()
    log.info("catalog.ingest.start", game=game, limit=limit)

    rows: list[dict[str, Any]] = []
    total = 0
    try:
        async for card in ingester.iter_cards(limit=limit):
            rows.append(ingester.to_row(card))
            if len(rows) >= batch_size:
                async with card_session() as session:
                    total += await upsert_cards(session, rows)
                log.info("catalog.ingest.flush", game=game, total=total)
                rows.clear()

        if rows:
            async with card_session() as session:
                total += await upsert_cards(session, rows)
    finally:
        await ingester.client.aclose()
    log.info("catalog.ingest.done", game=game, total=total)
    return total


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser("ingest:catalog")
    parser.add_argument("--game", required=True, choices=sorted(REGISTRY))
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args(argv)
    written = asyncio.run(ingest_game(args.game, limit=args.limit))
    log.info("catalog.cli.done", upserted=written, game=args.game)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
