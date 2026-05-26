from __future__ import annotations

import os

import structlog
from temporalio.client import Client
from temporalio.worker import Worker

from tcgscan_worker.workflows import (
    CatalogIngestWorkflow,
    EbayActiveWorkflow,
    EbaySoldWorkflow,
    MarketplacePricingWorkflow,
    RollupWorkflow,
)
from tcgscan_worker.workflows.activities import (
    activity_embed_catalog,
    activity_ingest_catalog,
    activity_ingest_pricing_batch,
    activity_rollup_daily,
)

log = structlog.get_logger()

TASK_QUEUE = "tcgscan-default"


async def run_worker() -> None:
    address = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    namespace = os.getenv("TEMPORAL_NAMESPACE", "default")
    if not address:
        log.warning("worker.skip", reason="TEMPORAL_ADDRESS unset")
        return

    try:
        client = await Client.connect(address, namespace=namespace)
    except Exception as exc:
        log.warning("worker.connect_failed", error=str(exc), address=address)
        return

    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[
            CatalogIngestWorkflow,
            EbayActiveWorkflow,
            EbaySoldWorkflow,
            MarketplacePricingWorkflow,
            RollupWorkflow,
        ],
        activities=[
            activity_ingest_catalog,
            activity_embed_catalog,
            activity_rollup_daily,
            activity_ingest_pricing_batch,
        ],
    )
    log.info("worker.start", task_queue=TASK_QUEUE)
    await worker.run()
