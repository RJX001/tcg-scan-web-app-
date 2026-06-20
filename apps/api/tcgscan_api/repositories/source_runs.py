"""Source ingest run audit log."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError, ProgrammingError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from tcgscan_api.db.models import CardIdentity, SourceRun, SourceRunStatus

log = structlog.get_logger()

BATCH_CURSOR_PREFIX = "batch_cursor:"

_UNFINISHED_STATUSES = (
    SourceRunStatus.queued,
    SourceRunStatus.started,
    SourceRunStatus.running,
)


def _run_age_seconds(started_at: datetime | None) -> float | None:
    """Age of a run in seconds, comparing against a matching clock basis.

    Postgres ``timestamptz`` returns timezone-aware datetimes while the app and
    SQLite use naive ``datetime.now()`` values. Comparing the two directly raises
    ``TypeError``; matching the basis per value avoids that crash entirely.
    """
    if started_at is None:
        return None
    try:
        if started_at.tzinfo is not None:
            return (datetime.now(timezone.utc) - started_at).total_seconds()
        return (datetime.now() - started_at).total_seconds()
    except (TypeError, ValueError, OverflowError):  # pragma: no cover - defensive
        return None


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
        error_message: str | None = None,
    ) -> None:
        run = await self._session.get(SourceRun, run_id)
        if run is None:
            return
        run.inserted_count = inserted_count
        run.updated_count = updated_count
        run.skipped_count = skipped_count
        if error_message is not None:
            run.error_message = error_message[:1024]
        await self._session.commit()

    async def update_progress(
        self,
        run_id: uuid.UUID,
        *,
        inserted_count: int,
        updated_count: int,
        skipped_count: int,
        cursor_message: str | None = None,
    ) -> None:
        """Persist in-flight batch progress without finishing the run."""
        run = await self._session.get(SourceRun, run_id)
        if run is None:
            return
        run.status = SourceRunStatus.running
        run.inserted_count = inserted_count
        run.updated_count = updated_count
        run.skipped_count = skipped_count
        run.error_message = cursor_message[:1024] if cursor_message else None
        run.finished_at = None
        run.duration_ms = None
        run.started_at = datetime.now()
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
            await self._safe_rollback()

    async def _safe_rollback(self) -> None:
        try:
            await self._session.rollback()
        except Exception as exc:  # pragma: no cover - rollback should not raise
            log.warning("source_runs.rollback_failed", error=str(exc))

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

    async def last_failed(self, source_key: str, *, run_type: str | None = None) -> SourceRun | None:
        stmt = select(SourceRun).where(
            SourceRun.source_key == source_key,
            SourceRun.status == SourceRunStatus.failed,
        )
        if run_type:
            stmt = stmt.where(SourceRun.run_type == run_type)
        stmt = stmt.order_by(SourceRun.finished_at.desc()).limit(1)
        try:
            return (await self._session.execute(stmt)).scalar_one_or_none()
        except (ProgrammingError, DBAPIError, SQLAlchemyError) as exc:
            await self._rollback_on_db_error(exc)
            return None

    async def latest_failed_with_cursor(self, source_key: str) -> SourceRun | None:
        stmt = (
            select(SourceRun)
            .where(
                SourceRun.source_key == source_key,
                SourceRun.status == SourceRunStatus.failed,
                SourceRun.run_type == "full",
                SourceRun.error_message.isnot(None),
                SourceRun.error_message.contains(BATCH_CURSOR_PREFIX),
            )
            .order_by(SourceRun.finished_at.desc())
            .limit(1)
        )
        try:
            return (await self._session.execute(stmt)).scalar_one_or_none()
        except (ProgrammingError, DBAPIError, SQLAlchemyError) as exc:
            await self._rollback_on_db_error(exc)
            return None

    async def reopen_run(self, run_id: uuid.UUID, *, cursor_message: str | None) -> None:
        run = await self._session.get(SourceRun, run_id)
        if run is None:
            return
        run.status = SourceRunStatus.running
        run.error_message = cursor_message[:1024] if cursor_message else None
        run.finished_at = None
        run.duration_ms = None
        run.started_at = datetime.now()
        await self._session.commit()

    @staticmethod
    def _is_stale(started_at: datetime | None, older_than_seconds: int) -> bool:
        """A run is stale if it started more than ``older_than_seconds`` ago.

        Timezone-safe (handles aware Postgres timestamptz and naive SQLite/local
        values). A missing ``started_at`` is treated as stale so an abandoned run
        never blocks future imports forever.
        """
        age = _run_age_seconds(started_at)
        if age is None:
            return True
        return age >= max(0, older_than_seconds)

    @staticmethod
    def _preserved_cursor(error_message: str | None) -> str | None:
        if error_message and BATCH_CURSOR_PREFIX in error_message:
            idx = error_message.index(BATCH_CURSOR_PREFIX)
            return error_message[idx:]
        return None

    async def fail_stale_runs(
        self,
        source_key: str,
        *,
        older_than_seconds: int,
        error_message: str = "Reclaimed: import did not finish (stale run)",
        preserve_batch_cursor: bool = False,
    ) -> int:
        """Mark unfinished runs older than the cutoff as failed.

        Prevents an interrupted import (deploy/restart) from blocking future
        imports forever by leaving a run stuck in queued/started/running.

        Defensive by design: this is invoked from the admin status endpoint and
        must never raise. Any DB or data issue is logged and swallowed so the
        page still renders.
        """
        # Filter only by status in SQL; do the age comparison in Python so a
        # naive/aware mismatch against a timestamptz column can never crash.
        stmt = select(SourceRun).where(
            SourceRun.source_key == source_key,
            SourceRun.status.in_(_UNFINISHED_STATUSES),
        )
        try:
            rows = list((await self._session.execute(stmt)).scalars().all())
        except (ProgrammingError, DBAPIError, SQLAlchemyError) as exc:
            await self._rollback_on_db_error(exc)
            log.warning("source_runs.fail_stale_runs_query_failed", source=source_key, error=str(exc))
            return 0
        except Exception as exc:  # pragma: no cover - unexpected driver error
            await self._safe_rollback()
            log.warning("source_runs.fail_stale_runs_query_failed", source=source_key, error=str(exc))
            return 0

        now = datetime.now()
        reclaimed = 0
        for run in rows:
            try:
                if not self._is_stale(run.started_at, older_than_seconds):
                    continue
                run.status = SourceRunStatus.failed
                cursor = self._preserved_cursor(run.error_message) if preserve_batch_cursor else None
                run.error_message = (
                    f"{error_message} {cursor}".strip() if cursor else error_message
                )[:1024]
                run.finished_at = now
                reclaimed += 1
            except Exception as exc:  # pragma: no cover - per-row safety
                log.warning(
                    "source_runs.fail_stale_runs_row_failed", source=source_key, error=str(exc)
                )
                continue

        if reclaimed == 0:
            return 0

        try:
            await self._session.commit()
        except (ProgrammingError, DBAPIError, SQLAlchemyError) as exc:
            await self._rollback_on_db_error(exc)
            log.warning("source_runs.fail_stale_runs_commit_failed", source=source_key, error=str(exc))
            return 0
        except Exception as exc:  # pragma: no cover - unexpected driver error
            await self._safe_rollback()
            log.warning("source_runs.fail_stale_runs_commit_failed", source=source_key, error=str(exc))
            return 0
        return reclaimed

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
