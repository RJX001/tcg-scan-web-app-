from __future__ import annotations

from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from tcgscan_worker.workflows.activities import activity_run_digests


@workflow.defn
class DigestWorkflow:
    """Nightly digest for Pro users."""

    @workflow.run
    async def run(self) -> int:
        return await workflow.execute_activity(
            activity_run_digests,
            start_to_close_timeout=timedelta(minutes=30),
            heartbeat_timeout=timedelta(seconds=30),
        )
