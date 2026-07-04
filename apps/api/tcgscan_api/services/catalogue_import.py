"""Full catalogue import from external metadata APIs."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from tcgscan_api.db.models import SourceRun, SourceRunStatus
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
DEFAULT_POKEMON_BATCH_SIZE = 250
BATCH_CURSOR_PREFIX = "batch_cursor:"
# Reclaim runs that never finished (e.g. process restart mid-import) so a stuck
# "running" row never blocks future imports or hides "Last Full".
STALE_RUN_SECONDS = 600
STALE_RUN_ERROR_MESSAGE = "Import timed out or browser disconnected. Safe to retry."

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
    next_page_token: str | None = None
    complete: bool = True


def _public_status(status: SourceRunStatus | str) -> str:
    value = status.value if isinstance(status, SourceRunStatus) else str(status)
    if value == SourceRunStatus.started.value:
        return "running"
    return value


def encode_batch_cursor(page: int, batch_size: int) -> str:
    return f"{BATCH_CURSOR_PREFIX}page={page};size={batch_size}"


def decode_batch_cursor(message: str | None) -> tuple[int, int] | None:
    if not message or BATCH_CURSOR_PREFIX not in message:
        return None
    idx = message.index(BATCH_CURSOR_PREFIX)
    payload = message[idx + len(BATCH_CURSOR_PREFIX) :]
    parts: dict[str, str] = {}
    for segment in payload.split(";"):
        if "=" in segment:
            key, value = segment.split("=", 1)
            parts[key.strip()] = value.strip()
    if "page" not in parts or "size" not in parts:
        return None
    try:
        return int(parts["page"]), int(parts["size"])
    except ValueError:
        return None


def _normalize_rows(
    normalized: list[dict[str, Any]],
    *,
    optional_skipped: list[str] | None = None,
) -> tuple[list[dict[str, object]], int]:
    skipped = len(optional_skipped or [])
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
    return rows, skipped


async def _upsert_rows(
    session: AsyncSession,
    run_id: uuid.UUID,
    rows: list[dict[str, object]],
    *,
    skipped: int,
) -> tuple[int, int]:
    runs = SourceRunsRepo(session)
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
    return inserted_total, updated_total


async def recover_stale_catalogue_imports(session: AsyncSession) -> int:
    """Mark abandoned catalogue import runs as failed so admin UI can recover.

    Best-effort and defensive: a failure for one source is logged and skipped so
    the admin status endpoint always renders. Never raises.
    """
    runs = SourceRunsRepo(session)
    reclaimed = 0
    for source_key in SOURCE_GAMES:
        try:
            reclaimed += await runs.fail_stale_runs(
                source_key,
                older_than_seconds=STALE_RUN_SECONDS,
                error_message=STALE_RUN_ERROR_MESSAGE,
                preserve_batch_cursor=True,
            )
        except Exception as exc:  # pragma: no cover - fail_stale_runs is itself guarded
            log.warning(
                "catalogue_import.stale_recovery_failed", source=source_key, error=str(exc)
            )
            continue
    if reclaimed:
        log.info("catalogue_import.stale_runs_reclaimed", count=reclaimed)
    return reclaimed


@dataclass
class FetchResult:
    cards: list[dict[str, Any]]
    optional_skipped: list[str] | None = None


def _one_piece_import_message(imported: int, optional_skipped: list[str] | None) -> str:
    skipped = optional_skipped or []
    if skipped and any("promo" in label.lower() for label in skipped):
        return "Imported set/ST cards. Promo endpoint unavailable/skipped."
    if skipped:
        labels = ", ".join(skipped)
        return f"Imported {imported} catalogue cards. Optional endpoints skipped: {labels}."
    return f"Imported {imported} catalogue cards"


def _optional_skip_error_message(optional_skipped: list[str] | None) -> str | None:
    if not optional_skipped:
        return None
    labels = ", ".join(optional_skipped)
    if any("promo" in label.lower() for label in optional_skipped):
        return "Optional promo endpoint unavailable/skipped."
    return f"Optional endpoints skipped: {labels}."


async def _fetch_full_normalized(source_key: str, *, limit: int | None) -> FetchResult:
    if source_key == "pokemon":
        pokemon_client = PokemonClient()
        try:
            return FetchResult(cards=await pokemon_client.iter_cards(limit=limit))
        finally:
            await pokemon_client.aclose()
    if source_key == "scryfall":
        scryfall_client = ScryfallClient()
        try:
            return FetchResult(cards=await scryfall_client.iter_cards(limit=limit))
        finally:
            await scryfall_client.aclose()
    if source_key == "ygopro":
        ygo_client = YgoProDeckClient()
        try:
            return FetchResult(cards=await ygo_client.iter_all_cards(limit=limit))
        finally:
            await ygo_client.aclose()
    if source_key == "one_piece":
        op_client = OnePieceClient()
        try:
            result = await op_client.iter_all_cards(limit=limit)
            return FetchResult(
                cards=result.cards,
                optional_skipped=list(result.skipped_optional_endpoints),
            )
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
    optional_skipped: list[str] | None = None,
) -> ImportResult:
    runs = SourceRunsRepo(session)
    rows, skipped = _normalize_rows(normalized, optional_skipped=optional_skipped)

    if dry_run:
        finished = await runs.finish(
            run_id,
            status=SourceRunStatus.success,
            inserted_count=len(rows),
            updated_count=0,
            skipped_count=skipped,
            error_message=_optional_skip_error_message(optional_skipped) or "dry_run",
            started_at=started_at,
        )
        message = _one_piece_import_message(len(rows), optional_skipped) if optional_skipped else (
            f"Dry run: {len(rows)} cards ready to upsert"
        )
        return ImportResult(
            source_run_id=str(finished.id),
            status=SourceRunStatus.success.value,
            inserted_count=len(rows),
            updated_count=0,
            skipped_count=skipped,
            message=message,
            dry_run=True,
        )

    inserted_total, updated_total = await _upsert_rows(session, run_id, rows, skipped=skipped)

    finished = await runs.finish(
        run_id,
        status=SourceRunStatus.success,
        inserted_count=inserted_total,
        updated_count=updated_total,
        skipped_count=skipped,
        error_message=_optional_skip_error_message(optional_skipped),
        started_at=started_at,
    )
    imported = inserted_total + updated_total
    message = (
        _one_piece_import_message(imported, optional_skipped)
        if optional_skipped
        else f"Imported {imported} catalogue cards"
    )
    return ImportResult(
        source_run_id=str(finished.id),
        status=SourceRunStatus.success.value,
        inserted_count=inserted_total,
        updated_count=updated_total,
        skipped_count=skipped,
        message=message,
        dry_run=False,
    )


async def _pokemon_batched_import(
    session: AsyncSession,
    *,
    batch_size: int,
    page_token: str | None,
    source_run_id: uuid.UUID | None,
    dry_run: bool,
    force: bool,
) -> ImportResult:
    """Fetch and upsert one Pokémon TCG API page per request."""
    batch_size = max(1, min(batch_size, 250))
    runs = SourceRunsRepo(session)
    await runs.fail_stale_runs(
        "pokemon",
        older_than_seconds=STALE_RUN_SECONDS,
        error_message=STALE_RUN_ERROR_MESSAGE,
        preserve_batch_cursor=True,
    )

    continuing = page_token is not None and source_run_id is not None
    resuming = False
    run: SourceRun | None = None
    page = 1
    inserted_total = 0
    updated_total = 0
    skipped_total = 0
    started_at = datetime.now()

    if continuing:
        run = await runs.get(source_run_id)  # type: ignore[arg-type]
        if run is None or run.source_key != "pokemon" or run.dry_run != dry_run:
            raise ValueError("invalid source_run_id for Pokémon import continuation")
        try:
            page = int(page_token or "1")
        except ValueError as exc:
            raise ValueError("invalid page_token") from exc
        inserted_total = run.inserted_count
        updated_total = run.updated_count
        skipped_total = run.skipped_count
        started_at = run.started_at or started_at
    else:
        if not force and not dry_run:
            active = await runs.active_run("pokemon")
            if active is not None:
                cursor = decode_batch_cursor(active.error_message)
                next_page = str(cursor[0]) if cursor else None
                return ImportResult(
                    source_run_id=str(active.id),
                    status=_public_status(active.status),
                    inserted_count=active.inserted_count,
                    updated_count=active.updated_count,
                    skipped_count=active.skipped_count,
                    message=(
                        "Import already in progress. Continue with the next batch."
                        if next_page
                        else "Import already in progress"
                    ),
                    dry_run=active.dry_run,
                    next_page_token=next_page,
                    complete=False,
                )

            resumable = await runs.latest_failed_with_cursor("pokemon")
            if resumable is not None:
                cursor = decode_batch_cursor(resumable.error_message)
                if cursor is not None:
                    page, saved_batch_size = cursor
                    batch_size = saved_batch_size
                    await runs.reopen_run(
                        resumable.id,
                        cursor_message=encode_batch_cursor(page, batch_size),
                    )
                    run = await runs.get(resumable.id)
                    assert run is not None
                    run_id = run.id
                    inserted_total = run.inserted_count
                    updated_total = run.updated_count
                    skipped_total = run.skipped_count
                    started_at = run.started_at or started_at
                    continuing = True
                    resuming = True
                else:
                    resuming = False
            else:
                resuming = False
        else:
            resuming = False

        if not continuing:
            run = await runs.start(
                "pokemon",
                dry_run=dry_run,
                game=SOURCE_GAMES["pokemon"],
                run_type="full",
                status=SourceRunStatus.running,
            )
            started_at = run.started_at or started_at

    assert run is not None
    run_id = run.id

    pokemon_client = PokemonClient()
    try:
        page_result = await pokemon_client.fetch_page(page=page, page_size=batch_size)
    finally:
        await pokemon_client.aclose()

    if page_result.page_failed:
        skipped_total += 1
        if not continuing and inserted_total == 0 and updated_total == 0:
            finished = await runs.finish(
                run_id,
                status=SourceRunStatus.failed,
                inserted_count=0,
                updated_count=0,
                skipped_count=skipped_total,
                error_message=f"Pokémon API page {page} failed",
                started_at=started_at,
            )
            return ImportResult(
                source_run_id=str(finished.id),
                status=SourceRunStatus.failed.value,
                inserted_count=0,
                updated_count=0,
                skipped_count=skipped_total,
                message=f"Pokémon import failed on page {page}",
                dry_run=dry_run,
                complete=True,
            )
        if page > 500:
            finished = await runs.finish(
                run_id,
                status=SourceRunStatus.failed,
                inserted_count=inserted_total,
                updated_count=updated_total,
                skipped_count=skipped_total,
                error_message=f"Pokémon API page {page} failed repeatedly",
                started_at=started_at,
            )
            return ImportResult(
                source_run_id=str(finished.id),
                status=SourceRunStatus.failed.value,
                inserted_count=inserted_total,
                updated_count=updated_total,
                skipped_count=skipped_total,
                message=f"Pokémon import failed on page {page}",
                dry_run=dry_run,
                complete=True,
            )
        await runs.update_progress(
            run_id,
            inserted_count=inserted_total,
            updated_count=updated_total,
            skipped_count=skipped_total,
            cursor_message=encode_batch_cursor(page_result.next_page, batch_size),
        )
        return ImportResult(
            source_run_id=str(run_id),
            status=SourceRunStatus.running.value,
            inserted_count=inserted_total,
            updated_count=updated_total,
            skipped_count=skipped_total,
            message=f"Skipped failed Pokémon API page {page}. Continue with next batch.",
            dry_run=dry_run,
            next_page_token=str(page_result.next_page),
            complete=False,
        )

    rows, skipped_batch = _normalize_rows(page_result.cards)
    skipped_total += skipped_batch

    if dry_run:
        finished = await runs.finish(
            run_id,
            status=SourceRunStatus.success,
            inserted_count=len(rows),
            updated_count=0,
            skipped_count=skipped_total,
            error_message="dry_run",
            started_at=started_at,
        )
        return ImportResult(
            source_run_id=str(finished.id),
            status=SourceRunStatus.success.value,
            inserted_count=len(rows),
            updated_count=0,
            skipped_count=skipped_total,
            message=f"Dry run: {len(rows)} cards ready to upsert (page {page})",
            dry_run=True,
        )

    ins, upd = await _upsert_rows(session, run_id, rows, skipped=skipped_total)
    inserted_total += ins
    updated_total += upd

    if page_result.has_more:
        await runs.update_progress(
            run_id,
            inserted_count=inserted_total,
            updated_count=updated_total,
            skipped_count=skipped_total,
            cursor_message=encode_batch_cursor(page_result.next_page, batch_size),
        )
        batch_count = ins + upd
        resume_prefix = "Resuming timed-out import. " if resuming else ""
        return ImportResult(
            source_run_id=str(run_id),
            status=SourceRunStatus.running.value,
            inserted_count=inserted_total,
            updated_count=updated_total,
            skipped_count=skipped_total,
            message=(
                f"{resume_prefix}Imported Pokémon batch page {page} ({batch_count} cards this batch, "
                f"{inserted_total + updated_total} total). Continue with next batch."
            ),
            dry_run=False,
            next_page_token=str(page_result.next_page),
            complete=False,
        )

    finished = await runs.finish(
        run_id,
        status=SourceRunStatus.success,
        inserted_count=inserted_total,
        updated_count=updated_total,
        skipped_count=skipped_total,
        started_at=started_at,
    )
    return ImportResult(
        source_run_id=str(finished.id),
        status=SourceRunStatus.success.value,
        inserted_count=inserted_total,
        updated_count=updated_total,
        skipped_count=skipped_total,
        message=f"Pokémon full import complete: {inserted_total + updated_total} catalogue cards",
        dry_run=False,
        complete=True,
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
        fetched = await _fetch_full_normalized(source_key, limit=limit)
        result = await _process_rows(
            session,
            run_id,
            normalized=fetched.cards,
            dry_run=dry_run,
            started_at=started_at,
            optional_skipped=fetched.optional_skipped,
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
    batch_size: int | None = None,
    page_token: str | None = None,
    source_run_id: uuid.UUID | None = None,
) -> ImportResult:
    """Run a catalogue import and persist progress on ``source_runs``.

    Pokémon full imports fetch one API page per request so the admin UI and
    status endpoints stay responsive. Other sources run inline in safe batches.
    """
    if source_key not in SOURCE_GAMES:
        raise ValueError(f"unknown catalogue source: {source_key}")

    if source_key == "pokemon" and limit is None:
        return await _pokemon_batched_import(
            session,
            batch_size=batch_size or DEFAULT_POKEMON_BATCH_SIZE,
            page_token=page_token,
            source_run_id=source_run_id,
            dry_run=dry_run,
            force=force,
        )

    runs = SourceRunsRepo(session)
    await runs.fail_stale_runs(
        source_key,
        older_than_seconds=STALE_RUN_SECONDS,
        error_message=STALE_RUN_ERROR_MESSAGE,
        preserve_batch_cursor=True,
    )

    if not force and not dry_run and page_token is None:
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
                complete=False,
            )

    game = SOURCE_GAMES[source_key]
    run = await runs.start(
        source_key,
        dry_run=dry_run,
        game=game,
        run_type="full",
        status=SourceRunStatus.started if dry_run else SourceRunStatus.running,
    )
    run_id = run.id
    started_at = run.started_at or datetime.now()

    try:
        fetch_limit = (limit or 100) if dry_run else limit
        fetched = await _fetch_full_normalized(source_key, limit=fetch_limit)
        return await _process_rows(
            session,
            run_id,
            normalized=fetched.cards,
            dry_run=dry_run,
            started_at=started_at,
            optional_skipped=fetched.optional_skipped,
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


async def _source_run_stats(
    runs: SourceRunsRepo, row: dict[str, Any], source_key: str
) -> dict[str, Any]:
    active = await runs.active_run(source_key)
    last_sample = await runs.last_success(source_key, run_type="sample")
    last_full = await runs.last_success(source_key, run_type="full")
    last_failed = await runs.last_failed(source_key, run_type="full")
    import_status_message: str | None = None
    if last_failed and last_failed.error_message and STALE_RUN_ERROR_MESSAGE in last_failed.error_message:
        import_status_message = (
            "Previous import timed out or browser disconnected. Safe to retry."
        )
    return {
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
        "import_status_message": import_status_message,
    }


def _failed_source_stats(row: dict[str, Any]) -> dict[str, Any]:
    """Safe per-source row when this source's status queries failed."""
    return {
        **row,
        "last_sample_at": row.get("last_sample_at"),
        "last_full_at": row.get("last_full_at"),
        "current_run_status": "failed",
        "current_run_id": None,
        "import_status_message": "Status temporarily unavailable for this source.",
    }


async def catalogue_stats(session: AsyncSession) -> dict[str, Any]:
    """Extended stats for admin sources UI.

    Per-source failures are isolated: a source whose run queries fail is
    returned as failed instead of crashing the whole status payload.
    """
    from tcgscan_api.services.catalogue_ingest import catalogue_stats as base_stats

    base = await base_stats(session)
    runs = SourceRunsRepo(session)
    stats: list[dict[str, Any]] = []
    for row in base.get("catalog_stats", []):
        source_key = str(row.get("source_key", ""))
        try:
            stats.append(await _source_run_stats(runs, row, source_key))
        except Exception as exc:
            try:
                await session.rollback()
            except Exception:  # pragma: no cover - rollback should not raise
                pass
            log.warning(
                "catalogue_import.source_stats_failed", source=source_key, error=str(exc)
            )
            stats.append(_failed_source_stats(row))
    return {"catalog_stats": stats}
