import pytest

from tcgscan_worker.worker import run_worker


@pytest.mark.asyncio
async def test_run_worker_exits_nonzero_when_temporal_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Connect failure must crash visibly (exit 1), not idle as a healthy-looking no-op."""
    monkeypatch.setenv("TEMPORAL_ADDRESS", "localhost:1")  # nothing listens here
    with pytest.raises(SystemExit) as excinfo:
        await run_worker()
    assert excinfo.value.code == 1
