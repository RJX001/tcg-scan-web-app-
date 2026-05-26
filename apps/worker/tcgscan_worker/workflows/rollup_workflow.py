from __future__ import annotations

from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from tcgscan_worker.workflows.activities import activity_rollup_daily


@workflow.defn
class RollupWorkflow:
    """Daily roll-up: aggregates sale_event -> card_price_daily."""

    @workflow.run
    async def run(self) -> int:
        return await workflow.execute_activity(
            activity_rollup_daily,
            start_to_close_timeout=timedelta(hours=2),
            heartbeat_timeout=timedelta(seconds=30),
        )
