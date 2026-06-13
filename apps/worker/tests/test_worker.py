import pytest

from tcgscan_worker.worker import run_worker


@pytest.mark.asyncio
async def test_run_worker_scaffold() -> None:
    await run_worker()
