"""Catalogue ingest from external metadata sources into card_identity."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from tcgscan_api.db.models import SourceRunStatus
from tcgscan_api.repositories.cards import CardsRepo
from tcgscan_api.repositories.source_runs import SourceRunsRepo
from tcgscan_api.services.catalogue_normalizer import to_card_identity_row
from tcgscan_api.sources.dragon_ball_fusion_world import DragonBallFusionWorldClient
from tcgscan_api.sources.dragon_ball_masters import DragonBallMastersClient
from tcgscan_api.sources.one_piece import OnePieceClient, normalize_card as normalize_one_piece
from tcgscan_api.sources.pokemon import PokemonClient
from tcgscan_api.sources.scryfall import ScryfallClient
from tcgscan_api.sources.ygoprodeck import YgoProDeckClient

log = structlog.get_logger()

MIN_COMPS_FOR_PRICE = 5


@dataclass
class IngestResult:
    source_run_id: str
    status: str
    inserted_count: int
    updated_count: int
    skipped_count: int
    message: str
    dry_run: bool = False


async def _fetch_normalized(source_key: str, *, limit: int) -> tuple[list[dict[str, Any]], str | None]:
    if source_key == "pokemon":
        pokemon_client = PokemonClient()
        try:
            return await pokemon_client.iter_cards(limit=limit), None
        finally:
            await pokemon_client.aclose()

    if source_key == "scryfall":
        scryfall_client = ScryfallClient()
        try:
            return await scryfall_client.iter_cards(limit=limit), None
        finally:
            await scryfall_client.aclose()

    if source_key == "ygopro":
        ygo_client = YgoProDeckClient()
        try:
            return (await ygo_client.iter_all_cards(limit=limit))[:limit], None
        finally:
            await ygo_client.aclose()

    if source_key == "one_piece":
        op_client = OnePieceClient()
        try:
            rows = await op_client.iter_all_cards(limit=limit)
            return rows[:limit] if limit else rows, None
        finally:
            await op_client.aclose()

    if source_key == "dragon_ball_fusion_world":
        fw_client = DragonBallFusionWorldClient()
        try:
            diag = await fw_client.diagnostic()
            if diag.get("status") not in {"success", "partial"}:
                return [], str(diag.get("message") or "Bandai Fusion World adapter not implemented")
            return [], "No catalogue rows available yet for Bandai Fusion World"
        finally:
            await fw_client.aclose()

    if source_key == "dragon_ball_masters":
        masters_client = DragonBallMastersClient()
        try:
            diag = await masters_client.diagnostic()
            if diag.get("status") not in {"success", "partial"}:
                return [], str(diag.get("message") or "Bandai Masters adapter not implemented")
            return [], "No catalogue rows available yet for Bandai Masters"
        finally:
            await masters_client.aclose()

    raise ValueError(f"unknown catalogue source: {source_key}")


async def run_catalogue_ingest(
    session: AsyncSession,
    source_key: str,
    *,
    limit: int = 100,
    dry_run: bool = False,
) -> IngestResult:
    limit = max(1, min(limit, 5000))
    runs = SourceRunsRepo(session)
    game_map = {
        "pokemon": "pokemon",
        "scryfall": "mtg",
        "ygopro": "yugioh",
        "one_piece": "one_piece",
    }
    run = await runs.start(
        source_key,
        dry_run=dry_run,
        game=game_map.get(source_key),
        run_type="dry_run" if dry_run else "sample",
    )
    started_at = run.started_at or datetime.now()
    inserted = 0
    updated = 0
    skipped = 0

    try:
        normalized, skip_message = await _fetch_normalized(source_key, limit=limit)
        if skip_message and not normalized:
            finished = await runs.finish(
                run.id,
                status=SourceRunStatus.partial,
                inserted_count=0,
                updated_count=0,
                skipped_count=limit,
                error_message=skip_message,
                started_at=started_at,
            )
            return IngestResult(
                source_run_id=str(finished.id),
                status=SourceRunStatus.partial.value,
                inserted_count=0,
                updated_count=0,
                skipped_count=limit,
                message=skip_message,
                dry_run=dry_run,
            )

        rows = []
        for item in normalized:
            if not item.get("source_card_id") or not item.get("name"):
                skipped += 1
                continue
            try:
                rows.append(to_card_identity_row(item))
            except (ValueError, KeyError) as exc:
                skipped += 1
                log.debug("catalogue_ingest.skip_row", source=source_key, error=str(exc))

        if dry_run:
            finished = await runs.finish(
                run.id,
                status=SourceRunStatus.success,
                inserted_count=len(rows),
                updated_count=0,
                skipped_count=skipped,
                error_message="dry_run",
                started_at=started_at,
            )
            return IngestResult(
                source_run_id=str(finished.id),
                status=SourceRunStatus.success.value,
                inserted_count=len(rows),
                updated_count=0,
                skipped_count=skipped,
                message=f"Dry run: {len(rows)} cards ready to upsert",
                dry_run=True,
            )

        inserted, updated = await CardsRepo(session).upsert_catalog_batch(rows)
        finished = await runs.finish(
            run.id,
            status=SourceRunStatus.success,
            inserted_count=inserted,
            updated_count=updated,
            skipped_count=skipped,
            started_at=started_at,
        )
        return IngestResult(
            source_run_id=str(finished.id),
            status=SourceRunStatus.success.value,
            inserted_count=inserted,
            updated_count=updated,
            skipped_count=skipped,
            message=f"Ingested {inserted + updated} cards from {source_key}",
            dry_run=False,
        )
    except Exception as exc:
        log.warning("catalogue_ingest.failed", source=source_key, error=str(exc))
        finished = await runs.finish(
            run.id,
            status=SourceRunStatus.failed,
            inserted_count=inserted,
            updated_count=updated,
            skipped_count=skipped,
            error_message=str(exc),
            started_at=started_at,
        )
        return IngestResult(
            source_run_id=str(finished.id),
            status=SourceRunStatus.failed.value,
            inserted_count=inserted,
            updated_count=updated,
            skipped_count=skipped,
            message=str(exc),
            dry_run=dry_run,
        )


async def catalogue_stats(session: AsyncSession) -> dict[str, Any]:
    runs = SourceRunsRepo(session)
    sources = {
        "pokemon": "pokemontcg",
        "scryfall": "scryfall",
        "ygopro": "ygoprodeck",
        "one_piece": "optcgapi",
        "dragon_ball_fusion_world": "bandai",
        "dragon_ball_masters": "bandai",
    }
    stats: list[dict[str, Any]] = []
    for source_key, catalog_source in sources.items():
        last = await runs.last_success(source_key)
        stats.append(
            {
                "source_key": source_key,
                "catalog_source": catalog_source,
                "card_count": await runs.count_cards_by_source(catalog_source),
                "last_success_at": last.finished_at.isoformat() if last and last.finished_at else None,
                "last_run_id": str(last.id) if last else None,
            }
        )
    return {"catalog_stats": stats}
