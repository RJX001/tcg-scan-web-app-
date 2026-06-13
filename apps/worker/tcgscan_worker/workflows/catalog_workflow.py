from __future__ import annotations

from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from tcgscan_worker.workflows.activities import (
        activity_embed_catalog,
        activity_ingest_catalog,
    )


@workflow.defn
class CatalogIngestWorkflow:
    """Weekly catalog refresh + embed for one game."""

    @workflow.run
    async def run(self, game: str, limit: int | None = None) -> dict[str, int]:
        ingested = await workflow.execute_activity(
            activity_ingest_catalog,
            args=[game, limit],
            start_to_close_timeout=timedelta(hours=1),
            heartbeat_timeout=timedelta(seconds=30),
        )
        embedded = await workflow.execute_activity(
            activity_embed_catalog,
            args=[game, limit],
            start_to_close_timeout=timedelta(hours=2),
            heartbeat_timeout=timedelta(seconds=30),
        )
        return {"ingested": ingested, "embedded": embedded}
