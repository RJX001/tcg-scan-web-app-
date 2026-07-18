from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics.export import MetricExporter, MetricExportResult
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

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


def _shutdown_otel_providers() -> None:
    provider = trace.get_tracer_provider()
    if hasattr(provider, "shutdown"):
        provider.shutdown()
    meter = metrics.get_meter_provider()
    if hasattr(meter, "shutdown"):
        meter.shutdown()


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
            SENTRY_DSN_API=None,
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
            SENTRY_DSN_API=None,
        ),
    )
    telemetry_mod._OTEL_READY = False

    init_observability()
    assert telemetry_mod._OTEL_READY is False


def test_init_observability_sets_providers_always_on(monkeypatch: object) -> None:
    from tcgscan_api import telemetry as telemetry_mod
    from tcgscan_api.config import Settings

    monkeypatch.setattr(  # type: ignore[attr-defined]
        telemetry_mod,
        "get_settings",
        lambda: Settings(
            _env_file=None,
            ENVIRONMENT="production",
            OTEL_EXPORTER_OTLP_ENDPOINT="http://127.0.0.1:4318",
            SENTRY_DSN_API=None,
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
    telemetry_mod._OTEL_READY = False
    telemetry_mod._HTTPX_INSTRUMENTED = False
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
        assert "MeterProvider" in type(metrics.get_meter_provider()).__name__
        # 100% sampling (ALWAYS_ON) in every environment, including production
        from opentelemetry.sdk.trace.sampling import ALWAYS_ON

        assert provider.sampler is ALWAYS_ON  # type: ignore[attr-defined]
        init_observability(app)
    finally:
        _shutdown_otel_providers()
        telemetry_mod._OTEL_READY = False


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
            SENTRY_DSN_API=None,
        ),
    )
    telemetry_mod._OTEL_READY = False

    def boom(_endpoint: str, _environment: str) -> None:
        raise RuntimeError("alloy unreachable during setup")

    monkeypatch.setattr(telemetry_mod, "_init_otel_providers", boom)  # type: ignore[attr-defined]

    # Must not raise — API boot continues without telemetry.
    init_observability(FastAPI())
    assert telemetry_mod._OTEL_READY is False
