"""eBay Browse API active listing ingest into marketplace_listings."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from tcgscan_api.config import get_settings
from tcgscan_api.db.models import SourceRunStatus
from tcgscan_api.repositories.marketplace_listings import MarketplaceListingsRepo
from tcgscan_api.repositories.source_runs import SourceRunsRepo
from tcgscan_api.services.ebay_normalizer import normalize_ebay_item_summary
from tcgscan_api.sources.ebay_browse import ebay_configured, search_item_summaries

log = structlog.get_logger()


@dataclass
class EbayIngestResult:
    source_run_id: str
    status: str
    inserted_count: int
    updated_count: int
    skipped_count: int
    message: str
    dry_run: bool = False


async def run_ebay_ingest(
    session: AsyncSession,
    *,
    query: str = "pokemon card charizard",
    limit: int = 25,
    dry_run: bool = False,
) -> EbayIngestResult:
    if not ebay_configured():
        return EbayIngestResult(
            source_run_id="",
            status="missing_env",
            inserted_count=0,
            updated_count=0,
            skipped_count=0,
            message="eBay not configured (set EBAY_OAUTH_TOKEN or EBAY_APP_ID+EBAY_CERT_ID)",
            dry_run=dry_run,
        )

    settings = get_settings()
    marketplace = settings.ebay_marketplace_id or "EBAY_GB"
    runs = SourceRunsRepo(session)
    run = await runs.start("ebay", dry_run=dry_run)
    started_at = run.started_at
    inserted = updated = skipped = 0

    try:
        items = await search_item_summaries(query=query, limit=limit, marketplace_id=marketplace)
        observed_at = datetime.now()
        normalized: list[dict[str, Any]] = []
        for item in items:
            row = normalize_ebay_item_summary(
                item, marketplace=marketplace, settings=settings, observed_at=observed_at
            )
            if row is None:
                skipped += 1
            else:
                normalized.append(row)

        if dry_run:
            finished = await runs.finish(
                run.id,
                status=SourceRunStatus.success,
                inserted_count=len(normalized),
                updated_count=0,
                skipped_count=skipped,
                error_message="dry_run",
                started_at=started_at,
            )
            return EbayIngestResult(
                source_run_id=str(finished.id),
                status=SourceRunStatus.success.value,
                inserted_count=len(normalized),
                updated_count=0,
                skipped_count=skipped,
                message=f"Dry run: {len(normalized)} listings ready to upsert",
                dry_run=True,
            )

        inserted, updated, extra_skipped = await MarketplaceListingsRepo(session).upsert_batch(
            normalized
        )
        skipped += extra_skipped
        finished = await runs.finish(
            run.id,
            status=SourceRunStatus.success,
            inserted_count=inserted,
            updated_count=updated,
            skipped_count=skipped,
            started_at=started_at,
        )
        return EbayIngestResult(
            source_run_id=str(finished.id),
            status=SourceRunStatus.success.value,
            inserted_count=inserted,
            updated_count=updated,
            skipped_count=skipped,
            message=f"Ingested {inserted + updated} eBay active listings",
            dry_run=False,
        )
    except Exception as exc:
        log.warning("ebay_ingest.failed", error=str(exc))
        finished = await runs.finish(
            run.id,
            status=SourceRunStatus.failed,
            inserted_count=inserted,
            updated_count=updated,
            skipped_count=skipped,
            error_message=str(exc),
            started_at=started_at,
        )
        return EbayIngestResult(
            source_run_id=str(finished.id),
            status=SourceRunStatus.failed.value,
            inserted_count=inserted,
            updated_count=updated,
            skipped_count=skipped,
            message=str(exc),
            dry_run=dry_run,
        )


async def ebay_listing_stats(session: AsyncSession) -> dict[str, Any]:
    runs = SourceRunsRepo(session)
    listings = MarketplaceListingsRepo(session)
    last = await runs.last_success("ebay")
    return {
        "pricing_stats": [
            {
                "source_key": "ebay",
                "listing_count": await listings.count_active(source="ebay"),
                "last_success_at": last.finished_at.isoformat() if last and last.finished_at else None,
                "last_run_id": str(last.id) if last else None,
            }
        ]
    }
