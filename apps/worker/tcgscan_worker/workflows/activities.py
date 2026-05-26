"""Temporal activities. Activities are at-least-once and idempotent."""

from __future__ import annotations

from temporalio import activity

from tcgscan_worker.catalog.runner import ingest_game
from tcgscan_worker.embedding import embed_game
from tcgscan_worker.pricing.ingest import ingest_batch
from tcgscan_worker.rollup import rollup_all


@activity.defn
async def activity_evaluate_alerts() -> int:
    activity.heartbeat()
    from tcgscan_worker.alerts.monitor import evaluate_all_alerts

    return await evaluate_all_alerts()


@activity.defn
async def activity_ingest_catalog(game: str, limit: int | None = None) -> int:
    activity.heartbeat()
    return await ingest_game(game, limit=limit)


@activity.defn
async def activity_embed_catalog(game: str, limit: int | None = None) -> int:
    activity.heartbeat()
    return await embed_game(game, limit=limit)


@activity.defn
async def activity_rollup_daily() -> int:
    activity.heartbeat()
    return await rollup_all()


@activity.defn
async def activity_ingest_pricing_batch(
    game: str | None, card_limit: int, sources: list[str]
) -> int:
    activity.heartbeat()
    return await ingest_batch(game=game, card_limit=card_limit, sources=sources)
