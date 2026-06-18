"""Source ingest run audit log."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError, ProgrammingError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from tcgscan_api.db.models import CardIdentity, SourceRun, SourceRunStatus


class SourceRunsRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def start(
        self,
        source_key: str,
        *,
        dry_run: bool = False,
        game: str | None = None,
        run_type: str = "sample",
        status: SourceRunStatus = SourceRunStatus.started,
    ) -> SourceRun:
        run = SourceRun(
            id=uuid.uuid4(),
            source_key=source_key,
            game=game,
            run_type="dry_run" if dry_run else run_type,
            status=status,
            dry_run=dry_run,
        )
        self._session.add(run)
        await self._session.commit()
        await self._session.refresh(run)
        return run

    async def set_status(self, run_id: uuid.UUID, status: SourceRunStatus) -> None:
        run = await self._session.get(SourceRun, run_id)
        if run is None:
            return
        run.status = status
        await self._session.commit()

    async def update_counts(
        self,
        run_id: uuid.UUID,
        *,
        inserted_count: int,
        updated_count: int,
        skipped_count: int,
    ) -> None:
        run = await self._session.get(SourceRun, run_id)
        if run is None:
            return
        run.inserted_count = inserted_count
        run.updated_count = updated_count
        run.skipped_count = skipped_count
        await self._session.commit()

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

    async def get(self, run_id: uuid.UUID) -> SourceRun | None:
        return await self._session.get(SourceRun, run_id)

    async def _rollback_on_db_error(self, exc: Exception) -> None:
        if isinstance(exc, (ProgrammingError, DBAPIError, SQLAlchemyError)):
            await self._session.rollback()

    async def last_success(self, source_key: str, *, run_type: str | None = None) -> SourceRun | None:
        stmt = select(SourceRun).where(
            SourceRun.source_key == source_key,
            SourceRun.status == SourceRunStatus.success,
        )
        if run_type:
            stmt = stmt.where(SourceRun.run_type == run_type)
        stmt = stmt.order_by(SourceRun.finished_at.desc()).limit(1)
        try:
            return (await self._session.execute(stmt)).scalar_one_or_none()
        except (ProgrammingError, DBAPIError, SQLAlchemyError) as exc:
            await self._rollback_on_db_error(exc)
            if run_type:
                return await self.last_success(source_key)
            return None

    async def fail_stale_runs(self, source_key: str, *, older_than_seconds: int) -> int:
        """Mark unfinished runs older than the cutoff as failed.

        Prevents an interrupted import (deploy/restart) from blocking future
        imports forever by leaving a run stuck in queued/started/running.
        """
        cutoff = datetime.now() - timedelta(seconds=older_than_seconds)
        stmt = select(SourceRun).where(
            SourceRun.source_key == source_key,
            SourceRun.status.in_(
                [SourceRunStatus.queued, SourceRunStatus.started, SourceRunStatus.running]
            ),
            SourceRun.started_at < cutoff,
        )
        try:
            rows = list((await self._session.execute(stmt)).scalars().all())
        except (ProgrammingError, DBAPIError, SQLAlchemyError) as exc:
            await self._rollback_on_db_error(exc)
            return 0
        if not rows:
            return 0
        now = datetime.now()
        for run in rows:
            run.status = SourceRunStatus.failed
            run.error_message = "Reclaimed: import did not finish (stale run)"
            run.finished_at = now
        await self._session.commit()
        return len(rows)

    async def active_run(self, source_key: str) -> SourceRun | None:
        stmt = (
            select(SourceRun)
            .where(
                SourceRun.source_key == source_key,
                SourceRun.status.in_(
                    [SourceRunStatus.queued, SourceRunStatus.started, SourceRunStatus.running]
                ),
            )
            .order_by(SourceRun.started_at.desc())
            .limit(1)
        )
        try:
            return (await self._session.execute(stmt)).scalar_one_or_none()
        except (ProgrammingError, DBAPIError, SQLAlchemyError) as exc:
            await self._rollback_on_db_error(exc)
            return None

    async def count_cards_by_source(self, source: str) -> int:
        stmt = select(func.count()).select_from(CardIdentity).where(CardIdentity.source == source)
        try:
            return int((await self._session.execute(stmt)).scalar_one())
        except (ProgrammingError, DBAPIError, SQLAlchemyError) as exc:
            await self._rollback_on_db_error(exc)
            return 0

    async def count_cards_by_game(self, game: str) -> int:
        stmt = select(func.count()).select_from(CardIdentity).where(CardIdentity.game == game)
        return int((await self._session.execute(stmt)).scalar_one())
