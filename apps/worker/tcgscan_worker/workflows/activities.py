"""Temporal activities. Activities are at-least-once and idempotent."""

from __future__ import annotations

import structlog
from temporalio import activity

from tcgscan_worker.catalog.runner import ingest_game
from tcgscan_worker.embedding import embed_game
from tcgscan_worker.pricing.ingest import ingest_batch
from tcgscan_worker.rollup import rollup_all

log = structlog.get_logger()


@activity.defn
async def activity_run_digests() -> int:
    activity.heartbeat()
    log.info("activity.start", activity="run_digests")
    from tcgscan_worker.digest.runner import run_daily_digests

    count = await run_daily_digests()
    log.info("activity.done", activity="run_digests", count=count)
    return count


@activity.defn
async def activity_evaluate_alerts() -> int:
    activity.heartbeat()
    log.info("activity.start", activity="evaluate_alerts")
    from tcgscan_worker.alerts.monitor import evaluate_all_alerts

    count = await evaluate_all_alerts()
    log.info("activity.done", activity="evaluate_alerts", count=count)
    return count


@activity.defn
async def activity_ingest_catalog(game: str, limit: int | None = None) -> int:
    activity.heartbeat()
    log.info("activity.start", activity="ingest_catalog", game=game, limit=limit)
    count = await ingest_game(game, limit=limit)
    log.info("activity.done", activity="ingest_catalog", game=game, count=count)
    return count


@activity.defn
async def activity_embed_catalog(game: str, limit: int | None = None) -> int:
    activity.heartbeat()
    log.info("activity.start", activity="embed_catalog", game=game, limit=limit)
    count = await embed_game(game, limit=limit)
    log.info("activity.done", activity="embed_catalog", game=game, count=count)
    return count


@activity.defn
async def activity_rollup_daily() -> int:
    activity.heartbeat()
    log.info("activity.start", activity="rollup_daily")
    count = await rollup_all()
    log.info("activity.done", activity="rollup_daily", count=count)
    return count


@activity.defn
async def activity_ingest_pricing_batch(
    game: str | None, card_limit: int, sources: list[str]
) -> int:
    activity.heartbeat()
    log.info(
        "activity.start",
        activity="ingest_pricing_batch",
        game=game,
        card_limit=card_limit,
        sources=sources,
    )
    count = await ingest_batch(game=game, card_limit=card_limit, sources=sources)
    log.info(
        "activity.done",
        activity="ingest_pricing_batch",
        game=game,
        count=count,
    )
    return count
