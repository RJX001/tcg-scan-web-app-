from __future__ import annotations

from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from tcgscan_worker.workflows.activities import activity_ingest_pricing_batch


@workflow.defn
class MarketplacePricingWorkflow:
    """Daily TCGPlayer + Cardmarket comp refresh."""

    @workflow.run
    async def run(self, game: str | None = None, card_limit: int = 5000) -> int:
        return await workflow.execute_activity(
            activity_ingest_pricing_batch,
            args=[game, card_limit, ["tcgplayer", "cardmarket"]],
            start_to_close_timeout=timedelta(hours=4),
            heartbeat_timeout=timedelta(seconds=30),
        )
