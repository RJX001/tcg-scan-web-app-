"""Telemetry coverage for scan.run and MLClient spans/metrics."""

from __future__ import annotations

import base64

import pytest
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from tcgscan_api.services import scan as scan_mod
from tcgscan_api.services.ml_client import MLClient
from tcgscan_api.services.scan import ScanInput, ScanResult, run_scan
from tests.telemetry_helpers import (
    MetricCapture,
    span_attr,
    span_by_name,
    span_names,
)


@pytest.fixture
def fake_image_b64() -> str:
    return base64.b64encode(b"fake-image-for-telemetry").decode()


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
async def test_run_scan_emits_spans_and_metrics_on_cache_miss(
    fake_image_b64: str,
    scan_stubs: None,
    in_memory_spans: InMemorySpanExporter,
    scan_metric_capture: MetricCapture,
) -> None:
    payload = ScanInput(image_b64=fake_image_b64, top_k=3)
    result = await run_scan(payload)

    assert isinstance(result, ScanResult)
    names = span_names(in_memory_spans)
    for expected in (
        "scan.run",
        "scan.detect",
        "scan.embed_ocr_grade",
        "scan.ann_search",
        "scan.rerank",
    ):
        assert expected in names, f"missing {expected}; got {names}"

    run_span = span_by_name(in_memory_spans, "scan.run")
    assert span_attr(run_span, "tcgscan.scan.cache_hit") is False
    assert span_attr(run_span, "tcgscan.scan.match_count") == len(result.matches)

    outcome_records = [
        attrs for _val, attrs in scan_metric_capture.histograms if attrs.get("tcgscan.scan.outcome")
    ]
    assert any(attrs.get("tcgscan.scan.outcome") == "ok" for attrs in outcome_records)

    counter_outcomes = [
        attrs.get("tcgscan.scan.outcome") for _val, attrs in scan_metric_capture.counters
    ]
    assert "ok" in counter_outcomes

    stage_names = {
        attrs.get("tcgscan.scan.stage")
        for _val, attrs in scan_metric_capture.histograms
        if "tcgscan.scan.stage" in attrs
    }
    assert {"detect", "embed_ocr_grade", "ann_search", "rerank"}.issubset(stage_names)


@pytest.mark.asyncio
async def test_run_scan_cache_hit_skips_detect_and_records_cache_hit_outcome(
    fake_image_b64: str,
    monkeypatch: pytest.MonkeyPatch,
    in_memory_spans: InMemorySpanExporter,
    scan_metric_capture: MetricCapture,
) -> None:
    cached_result = ScanResult(matches=[], condition={"overall": 8.5}, cached=True)

    async def fake_cache_get(_key: str) -> dict[str, object]:
        return cached_result.model_dump(mode="json")

    async def fail_cache_set(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("cache_set should not run on cache hit")

    monkeypatch.setattr(scan_mod, "cache_get", fake_cache_get)
    monkeypatch.setattr(scan_mod, "cache_set", fail_cache_set)

    payload = ScanInput(image_b64=fake_image_b64)
    result = await run_scan(payload)

    assert result.cached is True
    names = span_names(in_memory_spans)
    assert "scan.run" in names
    assert "scan.detect" not in names

    run_span = span_by_name(in_memory_spans, "scan.run")
    assert span_attr(run_span, "tcgscan.scan.cache_hit") is True

    counter_outcomes = [
        attrs.get("tcgscan.scan.outcome") for _val, attrs in scan_metric_capture.counters
    ]
    assert counter_outcomes == ["cache_hit"]


@pytest.mark.asyncio
async def test_ml_client_stub_mode_emits_span_and_metric(
    fake_image_b64: str,
    in_memory_spans: InMemorySpanExporter,
    ml_metric_capture: MetricCapture,
) -> None:
    client = MLClient()
    try:
        await client.detect(fake_image_b64)
    finally:
        await client.aclose()

    span = span_by_name(in_memory_spans, "ml.detect")
    assert span_attr(span, "tcgscan.ml.endpoint") == "detect"
    assert span_attr(span, "tcgscan.ml.mode") == "stub"

    assert ml_metric_capture.counters == [
        (1, {"tcgscan.ml.endpoint": "detect", "tcgscan.ml.mode": "stub"}),
    ]


@pytest.mark.asyncio
async def test_ml_client_fallback_mode_when_call_fails(
    fake_image_b64: str,
    monkeypatch: pytest.MonkeyPatch,
    in_memory_spans: InMemorySpanExporter,
    ml_metric_capture: MetricCapture,
) -> None:
    from tcgscan_api.config import Settings

    monkeypatch.setattr(
        "tcgscan_api.services.ml_client.get_settings",
        lambda: Settings(_env_file=None, MODAL_DETECT_URL="http://ml.test/detect"),
    )

    async def fail_call(_url: str | None, _payload: dict[str, object]) -> None:
        return None

    client = MLClient()
    monkeypatch.setattr(client, "_call", fail_call)
    try:
        await client.detect(fake_image_b64)
    finally:
        await client.aclose()

    span = span_by_name(in_memory_spans, "ml.detect")
    assert span_attr(span, "tcgscan.ml.endpoint") == "detect"
    assert span_attr(span, "tcgscan.ml.mode") == "fallback"

    assert ml_metric_capture.counters == [
        (1, {"tcgscan.ml.endpoint": "detect", "tcgscan.ml.mode": "fallback"}),
    ]
