"""Daily roll-up of `sale_event` -> `card_price_daily` (mean/median/min/max per grade bucket)."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime

import structlog
from sqlalchemy import select

from tcgscan_api.db.models import CardIdentity
from tcgscan_api.db.session import get_sessionmaker
from tcgscan_api.repositories.sales import SalesRepo

log = structlog.get_logger()


async def rollup_all(day: datetime | None = None, *, card_id: uuid.UUID | None = None) -> int:
    day = day or datetime.now()
    written = 0
    async with get_sessionmaker()() as session:
        if card_id is not None:
            ids = [card_id]
        else:
            ids = [row[0] for row in await session.execute(select(CardIdentity.id))]
        repo = SalesRepo(session)
        for cid in ids:
            written += await repo.rollup_day(cid, day)
    log.info("rollup.done", rows=written, day=day.isoformat())
    return written


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser("rollup:daily")
    parser.add_argument("--card-id", type=str, default=None)
    args = parser.parse_args(argv)
    cid = uuid.UUID(args.card_id) if args.card_id else None
    n = asyncio.run(rollup_all(card_id=cid))
    print(f"rolled_up_rows={n}")
    return 0
