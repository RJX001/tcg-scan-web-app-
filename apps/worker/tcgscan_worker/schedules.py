"""Register Temporal schedules for catalog, pricing, and rollups."""

from __future__ import annotations

from datetime import timedelta

import structlog
from temporalio.client import (
    Client,
    Schedule,
    ScheduleActionStartWorkflow,
    ScheduleIntervalSpec,
    ScheduleSpec,
)

from tcgscan_worker.worker import TASK_QUEUE

log = structlog.get_logger()

CATALOG_GAMES = ["pokemon", "mtg", "yugioh", "lorcana", "one_piece", "sports"]


async def register_schedules(client: Client) -> None:
    """Create Phase 1 schedules (Weeks 4–5). Skips IDs that already exist."""
    await _create(
        client,
        "ebay-active-popular",
        "EbayActiveWorkflow",
        args=[None, 1000],
        interval=timedelta(minutes=15),
    )
    await _create(
        client,
        "ebay-sold-hourly",
        "EbaySoldWorkflow",
        args=[None, 10000],
        interval=timedelta(hours=1),
    )
    await _create(
        client,
        "marketplace-pricing-daily",
        "MarketplacePricingWorkflow",
        args=[None, 5000],
        interval=timedelta(days=1),
    )
    await _create(
        client,
        "rollup-daily",
        "RollupWorkflow",
        args=[],
        interval=timedelta(days=1),
    )
    for game in CATALOG_GAMES:
        await _create(
            client,
            f"catalog-weekly-{game}",
            "CatalogIngestWorkflow",
            args=[game, None],
            interval=timedelta(days=7),
        )
    await _create(
        client,
        "alert-monitor",
        "AlertMonitorWorkflow",
        args=[],
        interval=timedelta(minutes=15),
    )
    log.info("schedules.registered", count=5 + len(CATALOG_GAMES))


async def _create(
    client: Client,
    schedule_id: str,
    workflow_name: str,
    *,
    args: list[object],
    interval: timedelta,
) -> None:
    schedule = Schedule(
        action=ScheduleActionStartWorkflow(
            workflow_name,
            args=args,
            id=f"{schedule_id}-run",
            task_queue=TASK_QUEUE,
        ),
        spec=ScheduleSpec(intervals=[ScheduleIntervalSpec(every=interval)]),
    )
    try:
        await client.create_schedule(schedule_id, schedule)
        log.info("schedules.created", id=schedule_id)
    except Exception as exc:
        log.info("schedules.skip", id=schedule_id, reason=str(exc))


async def main_async() -> None:
    import os

    address = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    namespace = os.getenv("TEMPORAL_NAMESPACE", "default")
    client = await Client.connect(address, namespace=namespace)
    await register_schedules(client)


def main() -> int:
    import asyncio

    asyncio.run(main_async())
    print("temporal schedules registered")
    return 0
