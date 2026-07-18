from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from types import SimpleNamespace

import pytest
import pytest_asyncio
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from tcgscan_api.db.session import Base
from tests.telemetry_helpers import MetricCapture, _is_sdk_tracer_provider


@pytest_asyncio.fixture
async def sqlite_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    async with Sessionmaker() as s:
        yield s
    await engine.dispose()


@pytest.fixture
def in_memory_spans() -> Iterator[InMemorySpanExporter]:
    """Attach an in-memory span exporter to the active (or fresh) SDK TracerProvider."""
    exporter = InMemorySpanExporter()
    provider = trace.get_tracer_provider()
    processor = SimpleSpanProcessor(exporter)

    if _is_sdk_tracer_provider(provider):
        provider.add_span_processor(processor)  # type: ignore[union-attr]
    else:
        sdk_provider = TracerProvider()
        sdk_provider.add_span_processor(processor)
        trace.set_tracer_provider(sdk_provider)

    yield exporter

    exporter.clear()
    if hasattr(processor, "shutdown"):
        processor.shutdown()


@pytest.fixture
def scan_metric_capture(monkeypatch: pytest.MonkeyPatch) -> MetricCapture:
    """Order-proof metric assertions for scan.run instrumentation."""
    from tcgscan_api.services import scan as scan_mod

    capture = MetricCapture()
    monkeypatch.setattr(scan_mod, "SCAN_DURATION", SimpleNamespace(record=capture.record))
    monkeypatch.setattr(scan_mod, "SCAN_STAGE_DURATION", SimpleNamespace(record=capture.record))
    monkeypatch.setattr(scan_mod, "SCAN_COUNT", SimpleNamespace(add=capture.add))
    return capture


@pytest.fixture
def ml_metric_capture(monkeypatch: pytest.MonkeyPatch) -> MetricCapture:
    """Order-proof metric assertions for MLClient instrumentation."""
    from tcgscan_api.services import ml_client as ml_mod

    capture = MetricCapture()
    monkeypatch.setattr(ml_mod, "ML_REQUESTS", SimpleNamespace(add=capture.add))
    return capture
