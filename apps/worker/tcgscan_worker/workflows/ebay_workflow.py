from __future__ import annotations

from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from tcgscan_worker.workflows.activities import activity_ingest_pricing_batch


@workflow.defn
class EbayActiveWorkflow:
    """Active listings poll. Top-1k popular cards every 15 min, long-tail every 6h."""

    @workflow.run
    async def run(self, game: str | None = None, card_limit: int = 1000) -> int:
        return await workflow.execute_activity(
            activity_ingest_pricing_batch,
            args=[game, card_limit, ["ebay_active"]],
            start_to_close_timeout=timedelta(hours=2),
            heartbeat_timeout=timedelta(seconds=30),
        )


@workflow.defn
class EbaySoldWorkflow:
    """Sold comps poll. Top-10k hourly, rest daily."""

    @workflow.run
    async def run(self, game: str | None = None, card_limit: int = 10000) -> int:
        return await workflow.execute_activity(
            activity_ingest_pricing_batch,
            args=[game, card_limit, ["ebay_sold"]],
            start_to_close_timeout=timedelta(hours=4),
            heartbeat_timeout=timedelta(seconds=30),
        )
