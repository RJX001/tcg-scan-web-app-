from __future__ import annotations

import json
import logging
import re
from typing import Any

import pytest
import structlog
from fastapi import FastAPI
from opentelemetry import _logs, metrics, trace
from opentelemetry.sdk.metrics.export import MetricExporter, MetricExportResult
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.sdk.trace.sampling import ParentBased

from tcgscan_api.telemetry import _otel_endpoint_configured, _otlp_base_url, init_observability


class _NoOpSpanExporter(SpanExporter):
    """Avoid real OTLP HTTP retries against localhost during unit tests."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__()

    def export(self, spans: Any) -> SpanExportResult:
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        return None

    def force_flush(self, timeout_millis: int = 30_000) -> bool:
        return True


class _NoOpMetricExporter(MetricExporter):
    """Avoid real OTLP HTTP retries against localhost during unit tests."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__()

    def export(
        self, metrics_data: Any, timeout_millis: float = 10_000, **kwargs: Any
    ) -> MetricExportResult:
        return MetricExportResult.SUCCESS

    def shutdown(self, timeout_millis: float = 30_000, **kwargs: Any) -> None:
        return None

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        return True


class _NoOpLogExporter:
    """Avoid real OTLP HTTP retries against localhost during unit tests."""

    def __init__(self, **kwargs: Any) -> None:
        pass

    def export(self, batch: Any) -> Any:
        from opentelemetry.sdk._logs.export import LogExportResult

        return LogExportResult.SUCCESS

    def shutdown(self) -> None:
        return None

    def force_flush(self, timeout_millis: int = 10_000) -> bool:
        return True


def _shutdown_otel_providers() -> None:
    provider = trace.get_tracer_provider()
    if hasattr(provider, "shutdown"):
        provider.shutdown()
    meter = metrics.get_meter_provider()
    if hasattr(meter, "shutdown"):
        meter.shutdown()
    logger_provider = _logs.get_logger_provider()
    if hasattr(logger_provider, "shutdown"):
        logger_provider.shutdown()


def test_otlp_base_url_strips_trailing_slash() -> None:
    assert _otlp_base_url("http://alloy.railway.internal:4318/") == (
        "http://alloy.railway.internal:4318"
    )
    assert _otlp_base_url("http://alloy.railway.internal:4318") == (
        "http://alloy.railway.internal:4318"
    )


def test_otel_endpoint_configured_treats_blank_as_unset() -> None:
    assert _otel_endpoint_configured(None) is None
    assert _otel_endpoint_configured("") is None
    assert _otel_endpoint_configured("   ") is None
    assert _otel_endpoint_configured("http://alloy:4318") == "http://alloy:4318"


def test_init_observability_noop_without_endpoint(monkeypatch: object) -> None:
    from tcgscan_api import telemetry as telemetry_mod
    from tcgscan_api.config import Settings

    monkeypatch.setattr(  # type: ignore[attr-defined]
        telemetry_mod,
        "get_settings",
        lambda: Settings(
            _env_file=None,
            ENVIRONMENT="development",
            OTEL_EXPORTER_OTLP_ENDPOINT=None,
        ),
    )
    telemetry_mod._OTEL_READY = False

    # Must not raise — local runs without Alloy.
    init_observability(FastAPI())
    assert telemetry_mod._OTEL_READY is False


def test_init_observability_noop_with_blank_endpoint(monkeypatch: object) -> None:
    from tcgscan_api import telemetry as telemetry_mod
    from tcgscan_api.config import Settings

    monkeypatch.setattr(  # type: ignore[attr-defined]
        telemetry_mod,
        "get_settings",
        lambda: Settings(
            _env_file=None,
            ENVIRONMENT="production",
            OTEL_EXPORTER_OTLP_ENDPOINT="  ",
        ),
    )
    telemetry_mod._OTEL_READY = False

    init_observability()
    assert telemetry_mod._OTEL_READY is False


def test_init_observability_sets_providers_with_sdk_default_sampler(monkeypatch: object) -> None:
    from tcgscan_api import telemetry as telemetry_mod
    from tcgscan_api.config import Settings
    from opentelemetry.sdk._logs import LoggerProvider

    monkeypatch.setattr(  # type: ignore[attr-defined]
        telemetry_mod,
        "get_settings",
        lambda: Settings(
            _env_file=None,
            ENVIRONMENT="production",
            OTEL_EXPORTER_OTLP_ENDPOINT="http://127.0.0.1:4318",
        ),
    )
    monkeypatch.setattr(
        "opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter",
        _NoOpSpanExporter,
    )
    monkeypatch.setattr(
        "opentelemetry.exporter.otlp.proto.http.metric_exporter.OTLPMetricExporter",
        _NoOpMetricExporter,
    )
    monkeypatch.setattr(
        "opentelemetry.exporter.otlp.proto.http._log_exporter.OTLPLogExporter",
        _NoOpLogExporter,
    )
    telemetry_mod._OTEL_READY = False
    telemetry_mod._HTTPX_INSTRUMENTED = False
    telemetry_mod._SQLALCHEMY_INSTRUMENTED = False
    telemetry_mod._REDIS_INSTRUMENTED = False
    telemetry_mod._LOG_HANDLER_ATTACHED = False
    telemetry_mod._INSTRUMENTED_APP_IDS.clear()

    app = FastAPI()

    @app.get("/v1/cards")
    async def cards() -> dict[str, str]:
        return {"ok": "yes"}

    try:
        init_observability(app)

        assert telemetry_mod._OTEL_READY is True
        provider = trace.get_tracer_provider()
        assert "TracerProvider" in type(provider).__name__
        assert isinstance(provider.sampler, ParentBased)  # type: ignore[attr-defined]
        assert "MeterProvider" in type(metrics.get_meter_provider()).__name__
        assert isinstance(_logs.get_logger_provider(), LoggerProvider)
        init_observability(app)
    finally:
        _shutdown_otel_providers()
        telemetry_mod._OTEL_READY = False
        telemetry_mod._LOG_HANDLER_ATTACHED = False


def test_init_observability_swallows_setup_errors(monkeypatch: object) -> None:
    from tcgscan_api import telemetry as telemetry_mod
    from tcgscan_api.config import Settings

    monkeypatch.setattr(  # type: ignore[attr-defined]
        telemetry_mod,
        "get_settings",
        lambda: Settings(
            _env_file=None,
            ENVIRONMENT="development",
            OTEL_EXPORTER_OTLP_ENDPOINT="http://127.0.0.1:4318",
        ),
    )
    telemetry_mod._OTEL_READY = False

    def boom(_endpoint: str, _environment: str) -> None:
        raise RuntimeError("alloy unreachable during setup")

    monkeypatch.setattr(telemetry_mod, "_init_otel_providers", boom)  # type: ignore[attr-defined]

    # Must not raise — API boot continues without telemetry.
    init_observability(FastAPI())
    assert telemetry_mod._OTEL_READY is False


def test_configure_logging_injects_trace_context(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    in_memory_spans: object,
) -> None:
    from tcgscan_api import logging_setup as logging_mod
    from tcgscan_api.logging_setup import configure_logging

    root = logging.getLogger()
    saved_handlers = list(root.handlers)
    saved_level = root.level

    monkeypatch.setattr(logging_mod, "_LOGGING_CONFIGURED", False)
    configure_logging()

    tracer = trace.get_tracer("tcgscan_api.test")
    with tracer.start_as_current_span("log.correlation.test"):
        structlog.get_logger("tcgscan.test").info("telemetry.log.correlation")

    out = capsys.readouterr().out
    payload: dict[str, object] | None = None
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            candidate = json.loads(line)
        except json.JSONDecodeError:
            continue
        if candidate.get("event") == "telemetry.log.correlation":
            payload = candidate
            break

    assert payload is not None, f"expected correlation log in stdout, got: {out!r}"
    assert re.fullmatch(r"[0-9a-f]{32}", str(payload["trace_id"]))
    assert re.fullmatch(r"[0-9a-f]{16}", str(payload["span_id"]))

    root.handlers.clear()
    for handler in saved_handlers:
        root.addHandler(handler)
    root.setLevel(saved_level)
