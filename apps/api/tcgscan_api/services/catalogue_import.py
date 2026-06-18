"""Full catalogue import from external metadata APIs."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from tcgscan_api.db.models import SourceRunStatus
from tcgscan_api.db.session import get_sessionmaker
from tcgscan_api.repositories.cards import CardsRepo
from tcgscan_api.repositories.source_runs import SourceRunsRepo
from tcgscan_api.services.catalogue_normalizer import to_card_identity_row
from tcgscan_api.sources.one_piece import OnePieceClient
from tcgscan_api.sources.pokemon import PokemonClient
from tcgscan_api.sources.scryfall import ScryfallClient
from tcgscan_api.sources.ygoprodeck import YgoProDeckClient

log = structlog.get_logger()

BATCH_UPSERT_SIZE = 500
PROGRESS_UPDATE_EVERY = 500
# Reclaim runs that never finished (e.g. process restart mid-import) so a stuck
# "running" row never blocks future imports or hides "Last Full".
STALE_RUN_SECONDS = 1800

SOURCE_GAMES: dict[str, str] = {
    "pokemon": "pokemon",
    "scryfall": "mtg",
    "ygopro": "yugioh",
    "one_piece": "one_piece",
}

IMPORT_ROUTE_KEYS: dict[str, str] = {
    "pokemon": "pokemon",
    "scryfall": "scryfall",
    "ygopro": "ygopro",
    "one-piece": "one_piece",
}


@dataclass
class ImportResult:
    source_run_id: str
    status: str
    inserted_count: int
    updated_count: int
    skipped_count: int
    message: str
    dry_run: bool = False


def _public_status(status: SourceRunStatus | str) -> str:
    value = status.value if isinstance(status, SourceRunStatus) else str(status)
    if value == SourceRunStatus.started.value:
        return "running"
    return value


async def _fetch_full_normalized(source_key: str, *, limit: int | None) -> list[dict[str, Any]]:
    if source_key == "pokemon":
        pokemon_client = PokemonClient()
        try:
            return await pokemon_client.iter_cards(limit=limit)
        finally:
            await pokemon_client.aclose()
    if source_key == "scryfall":
        scryfall_client = ScryfallClient()
        try:
            return await scryfall_client.iter_cards(limit=limit)
        finally:
            await scryfall_client.aclose()
    if source_key == "ygopro":
        ygo_client = YgoProDeckClient()
        try:
            return await ygo_client.iter_all_cards(limit=limit)
        finally:
            await ygo_client.aclose()
    if source_key == "one_piece":
        op_client = OnePieceClient()
        try:
            return await op_client.iter_all_cards(limit=limit)
        finally:
            await op_client.aclose()
    raise ValueError(f"full import not supported for source: {source_key}")


async def _process_rows(
    session: AsyncSession,
    run_id: uuid.UUID,
    *,
    normalized: list[dict[str, Any]],
    dry_run: bool,
    started_at: datetime,
) -> ImportResult:
    runs = SourceRunsRepo(session)
    skipped = 0
    rows: list[dict[str, object]] = []
    for item in normalized:
        if not item.get("source_card_id") or not item.get("name"):
            skipped += 1
            continue
        try:
            rows.append(to_card_identity_row(item))
        except (ValueError, KeyError) as exc:
            skipped += 1
            log.debug("catalogue_import.skip_row", error=str(exc))

    if dry_run:
        finished = await runs.finish(
            run_id,
            status=SourceRunStatus.success,
            inserted_count=len(rows),
            updated_count=0,
            skipped_count=skipped,
            error_message="dry_run",
            started_at=started_at,
        )
        return ImportResult(
            source_run_id=str(finished.id),
            status=SourceRunStatus.success.value,
            inserted_count=len(rows),
            updated_count=0,
            skipped_count=skipped,
            message=f"Dry run: {len(rows)} cards ready to upsert",
            dry_run=True,
        )

    inserted_total = 0
    updated_total = 0
    cards = CardsRepo(session)
    for i in range(0, len(rows), BATCH_UPSERT_SIZE):
        batch = rows[i : i + BATCH_UPSERT_SIZE]
        ins, upd = await cards.upsert_catalog_batch(batch, commit_every=BATCH_UPSERT_SIZE)
        inserted_total += ins
        updated_total += upd
        if (i + len(batch)) % PROGRESS_UPDATE_EVERY == 0:
            await runs.update_counts(
                run_id,
                inserted_count=inserted_total,
                updated_count=updated_total,
                skipped_count=skipped,
            )

    finished = await runs.finish(
        run_id,
        status=SourceRunStatus.success,
        inserted_count=inserted_total,
        updated_count=updated_total,
        skipped_count=skipped,
        started_at=started_at,
    )
    return ImportResult(
        source_run_id=str(finished.id),
        status=SourceRunStatus.success.value,
        inserted_count=inserted_total,
        updated_count=updated_total,
        skipped_count=skipped,
        message=f"Imported {inserted_total + updated_total} catalogue cards",
        dry_run=False,
    )


async def execute_full_catalogue_import(
    run_id: uuid.UUID,
    source_key: str,
    *,
    limit: int | None = None,
    dry_run: bool = False,
    session: AsyncSession | None = None,
) -> None:
    """Background worker: fetch full catalogue and upsert in batches."""
    if session is not None:
        await _execute_full_catalogue_import(session, run_id, source_key, limit=limit, dry_run=dry_run)
        return
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db_session:
        await _execute_full_catalogue_import(
            db_session, run_id, source_key, limit=limit, dry_run=dry_run
        )


async def _execute_full_catalogue_import(
    session: AsyncSession,
    run_id: uuid.UUID,
    source_key: str,
    *,
    limit: int | None = None,
    dry_run: bool = False,
) -> None:
    runs = SourceRunsRepo(session)
    run = await runs.get(run_id)
    if run is None:
        return
    started_at = run.started_at or datetime.now()
    inserted = updated = skipped = 0
    try:
        await runs.set_status(run_id, SourceRunStatus.running)
        normalized = await _fetch_full_normalized(source_key, limit=limit)
        result = await _process_rows(
            session,
            run_id,
            normalized=normalized,
            dry_run=dry_run,
            started_at=started_at,
        )
        log.info(
            "catalogue_import.complete",
            source=source_key,
            status=result.status,
            inserted=result.inserted_count,
            updated=result.updated_count,
        )
    except Exception as exc:
        log.warning("catalogue_import.failed", source=source_key, error=str(exc))
        await session.rollback()
        await runs.finish(
            run_id,
            status=SourceRunStatus.failed,
            inserted_count=inserted,
            updated_count=updated,
            skipped_count=skipped,
            error_message=str(exc),
            started_at=started_at,
        )


async def start_full_catalogue_import(
    session: AsyncSession,
    source_key: str,
    *,
    limit: int | None = None,
    dry_run: bool = False,
    force: bool = False,
) -> ImportResult:
    """Run a full catalogue import synchronously and persist its source_run.

    There is no separate background worker for the API service, so imports run
    inline in safe batches and the run is finished (``success``/``failed``)
    before returning. This guarantees "Last Full" updates and that runs are
    never left stuck in ``running``.
    """
    if source_key not in SOURCE_GAMES:
        raise ValueError(f"unknown catalogue source: {source_key}")

    runs = SourceRunsRepo(session)
    await runs.fail_stale_runs(source_key, older_than_seconds=STALE_RUN_SECONDS)

    if not force and not dry_run:
        active = await runs.active_run(source_key)
        if active is not None:
            return ImportResult(
                source_run_id=str(active.id),
                status=_public_status(active.status),
                inserted_count=active.inserted_count,
                updated_count=active.updated_count,
                skipped_count=active.skipped_count,
                message="Import already in progress",
                dry_run=active.dry_run,
            )

    game = SOURCE_GAMES[source_key]
    run = await runs.start(
        source_key,
        dry_run=dry_run,
        game=game,
        run_type="full",
        status=SourceRunStatus.started if dry_run else SourceRunStatus.running,
    )
    # Capture before any rollback: rollback expires ORM attributes and a later
    # lazy reload would attempt sync IO outside the async greenlet context.
    run_id = run.id
    started_at = run.started_at or datetime.now()

    try:
        fetch_limit = (limit or 100) if dry_run else limit
        normalized = await _fetch_full_normalized(source_key, limit=fetch_limit)
        return await _process_rows(
            session,
            run_id,
            normalized=normalized,
            dry_run=dry_run,
            started_at=started_at,
        )
    except Exception as exc:
        log.warning("catalogue_import.failed", source=source_key, error=str(exc))
        await session.rollback()
        finished = await runs.finish(
            run_id,
            status=SourceRunStatus.failed,
            inserted_count=0,
            updated_count=0,
            skipped_count=0,
            error_message=str(exc),
            started_at=started_at,
        )
        return ImportResult(
            source_run_id=str(finished.id),
            status=SourceRunStatus.failed.value,
            inserted_count=0,
            updated_count=0,
            skipped_count=0,
            message=str(exc),
            dry_run=dry_run,
        )


async def catalogue_stats(session: AsyncSession) -> dict[str, Any]:
    """Extended stats for admin sources UI."""
    from tcgscan_api.services.catalogue_ingest import catalogue_stats as base_stats

    base = await base_stats(session)
    runs = SourceRunsRepo(session)
    stats: list[dict[str, Any]] = []
    for row in base.get("catalog_stats", []):
        source_key = str(row["source_key"])
        active = await runs.active_run(source_key)
        last_sample = await runs.last_success(source_key, run_type="sample")
        last_full = await runs.last_success(source_key, run_type="full")
        stats.append(
            {
                **row,
                "last_sample_at": (
                    last_sample.finished_at.isoformat()
                    if last_sample and last_sample.finished_at
                    else None
                ),
                "last_full_at": (
                    last_full.finished_at.isoformat() if last_full and last_full.finished_at else None
                ),
                "current_run_status": _public_status(active.status) if active else None,
                "current_run_id": str(active.id) if active else None,
            }
        )
    return {"catalog_stats": stats}
