"""Log severity coverage for worker runtime (W3 package)."""

from __future__ import annotations

import pytest
from structlog.testing import capture_logs

from tcgscan_worker.catalog.runner import ingest_game
from tcgscan_worker.worker import run_worker


def _events(cap: list[dict[str, object]], event: str, *, level: str) -> list[dict[str, object]]:
    return [
        entry for entry in cap if entry.get("event") == event and entry.get("log_level") == level
    ]


@pytest.mark.asyncio
async def test_ingest_unknown_game_logs_error() -> None:
    with capture_logs() as cap:
        with pytest.raises(ValueError, match="unknown game"):
            await ingest_game("not-a-game")

    errors = _events(cap, "catalog.unknown_game", level="error")
    assert len(errors) == 1
    assert errors[0]["game"] == "not-a-game"
    assert isinstance(errors[0]["known"], list)


@pytest.mark.asyncio
async def test_run_worker_empty_address_logs_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEMPORAL_ADDRESS", "")

    with capture_logs() as cap:
        await run_worker()

    errors = _events(cap, "worker.skip", level="error")
    assert len(errors) == 1
    assert errors[0]["reason"] == "TEMPORAL_ADDRESS unset"


@pytest.mark.asyncio
async def test_run_worker_connect_failure_logs_error_and_exits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail_connect(*_args: object, **_kwargs: object) -> None:
        raise ConnectionError("connection refused")

    monkeypatch.setattr("tcgscan_worker.worker.Client.connect", fail_connect)

    with capture_logs() as cap:
        with pytest.raises(SystemExit) as exc_info:
            await run_worker()

    assert exc_info.value.code == 1
    errors = _events(cap, "worker.connect_failed", level="error")
    assert len(errors) == 1
    assert errors[0]["address"] == "localhost:7233"
