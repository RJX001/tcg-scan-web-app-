"""Log-severity coverage for scan orchestrator (sre.md package A2)."""

from __future__ import annotations

import base64

import pytest
import structlog
from structlog.testing import capture_logs

from tcgscan_api.services import scan as scan_mod
from tcgscan_api.services.scan import ScanInput, ScanResult, run_scan


@pytest.fixture
def fake_image_b64() -> str:
    return base64.b64encode(b"fake-image-for-scan-logging").decode()


@pytest.fixture
def scan_stubs(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_search(**_kwargs: object) -> list[object]:
        return []

    async def noop_cache_get(_key: str) -> None:
        return None

    async def noop_cache_set(_key: str, _value: object, ttl_s: int = 900) -> None:
        return None

    monkeypatch.setattr(scan_mod, "search_similar", fake_search)
    monkeypatch.setattr(scan_mod, "cache_get", noop_cache_get)
    monkeypatch.setattr(scan_mod, "cache_set", noop_cache_set)


@pytest.mark.asyncio
async def test_qdrant_unavailable_logs_error(
    fake_image_b64: str,
    monkeypatch: pytest.MonkeyPatch,
    scan_stubs: None,
) -> None:
    async def boom_search(**_kwargs: object) -> list[object]:
        raise RuntimeError("qdrant down")

    monkeypatch.setattr(scan_mod, "search_similar", boom_search)

    with capture_logs() as cap_logs:
        monkeypatch.setattr(scan_mod, "log", structlog.get_logger("test.scan.logging"))
        result = await run_scan(ScanInput(image_b64=fake_image_b64, top_k=3))

    assert isinstance(result, ScanResult)
    assert result.cached is False
    qdrant_events = [e for e in cap_logs if e.get("event") == "scan.qdrant_unavailable"]
    assert len(qdrant_events) == 1
    assert qdrant_events[0]["log_level"] == "error"


@pytest.mark.asyncio
async def test_corrupt_cache_payload_logs_warning_and_recomputes(
    fake_image_b64: str,
    monkeypatch: pytest.MonkeyPatch,
    scan_stubs: None,
) -> None:
    async def corrupt_cache_get(_key: str) -> dict[str, object]:
        return {"matches": "not-a-list", "condition": None}

    monkeypatch.setattr(scan_mod, "cache_get", corrupt_cache_get)

    with capture_logs() as cap_logs:
        monkeypatch.setattr(scan_mod, "log", structlog.get_logger("test.scan.logging"))
        result = await run_scan(ScanInput(image_b64=fake_image_b64, top_k=3))

    assert isinstance(result, ScanResult)
    assert result.cached is False
    assert result.stages_ms is not None
    assert "detect" in result.stages_ms

    cache_events = [e for e in cap_logs if e.get("event") == "scan.cache_payload_invalid"]
    assert len(cache_events) == 1
    assert cache_events[0]["log_level"] == "warning"
    assert "key" in cache_events[0]
    assert "error" in cache_events[0]
