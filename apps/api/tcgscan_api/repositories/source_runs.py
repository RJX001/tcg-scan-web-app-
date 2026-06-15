"""Source ingest run audit log."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tcgscan_api.db.models import CardIdentity, SourceRun, SourceRunStatus


class SourceRunsRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def start(self, source_key: str, *, dry_run: bool = False) -> SourceRun:
        run = SourceRun(
            id=uuid.uuid4(),
            source_key=source_key,
            status=SourceRunStatus.started,
            dry_run=dry_run,
        )
        self._session.add(run)
        await self._session.commit()
        await self._session.refresh(run)
        return run

    async def finish(
        self,
        run_id: uuid.UUID,
        *,
        status: SourceRunStatus,
        inserted_count: int,
        updated_count: int,
        skipped_count: int,
        error_message: str | None = None,
        started_at: datetime,
    ) -> SourceRun:
        run = await self._session.get(SourceRun, run_id)
        if run is None:
            raise ValueError(f"source run not found: {run_id}")
        finished_at = datetime.now()
        started = started_at.replace(tzinfo=None) if started_at.tzinfo else started_at
        run.status = status
        run.inserted_count = inserted_count
        run.updated_count = updated_count
        run.skipped_count = skipped_count
        run.error_message = error_message[:1024] if error_message else None
        run.finished_at = finished_at
        run.duration_ms = int((finished_at - started).total_seconds() * 1000)
        await self._session.commit()
        await self._session.refresh(run)
        return run

    async def last_success(self, source_key: str) -> SourceRun | None:
        stmt = (
            select(SourceRun)
            .where(
                SourceRun.source_key == source_key,
                SourceRun.status == SourceRunStatus.success,
            )
            .order_by(SourceRun.finished_at.desc())
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def count_cards_by_source(self, source: str) -> int:
        stmt = select(func.count()).select_from(CardIdentity).where(CardIdentity.source == source)
        return int((await self._session.execute(stmt)).scalar_one())

    async def count_cards_by_game(self, game: str) -> int:
        stmt = select(func.count()).select_from(CardIdentity).where(CardIdentity.game == game)
        return int((await self._session.execute(stmt)).scalar_one())
