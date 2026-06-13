from __future__ import annotations

from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from tcgscan_worker.workflows.activities import activity_evaluate_alerts


@workflow.defn
class AlertMonitorWorkflow:
    """Poll active price alerts and log triggers (email delivery in Phase 2)."""

    @workflow.run
    async def run(self) -> int:
        return await workflow.execute_activity(
            activity_evaluate_alerts,
            start_to_close_timeout=timedelta(minutes=15),
            heartbeat_timeout=timedelta(seconds=30),
        )
