"""Sentry + OpenTelemetry bootstrap (traces + metrics via OTLP HTTP)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from tcgscan_api.config import get_settings

if TYPE_CHECKING:
    from fastapi import FastAPI

log = structlog.get_logger()

_OTEL_READY = False
_HTTPX_INSTRUMENTED = False
_INSTRUMENTED_APP_IDS: set[int] = set()


def _otlp_base_url(endpoint: str) -> str:
    """Normalize OTEL_EXPORTER_OTLP_ENDPOINT to a base URL without trailing slash."""
    return endpoint.rstrip("/")


def _otel_endpoint_configured(raw: str | None) -> str | None:
    """Return a usable OTLP base URL, or None when unset/blank (local default)."""
    if raw is None:
        return None
    endpoint = raw.strip()
    return endpoint or None


def init_observability(app: FastAPI | None = None) -> None:
    """Initialize Sentry (optional) and OTEL providers + instrumentation (optional).

    Call once at startup after the FastAPI app (and routes) exist.

    When ``OTEL_EXPORTER_OTLP_ENDPOINT`` is unset/blank, this is a no-op so local
    runs without Alloy keep working. OTEL setup failures are logged and swallowed
    so observability never takes down the API.
    """
    global _OTEL_READY
    settings = get_settings()

    if settings.sentry_dsn_api:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.fastapi import FastApiIntegration

            sentry_sdk.init(
                dsn=settings.sentry_dsn_api,
                integrations=[FastApiIntegration()],
                traces_sample_rate=0.1,
                environment=settings.environment,
            )
            log.info("observability.sentry_enabled", environment=settings.environment)
        except Exception:
            log.exception("observability.sentry_failed")

    endpoint = _otel_endpoint_configured(settings.otel_exporter_otlp_endpoint)
    if endpoint is None:
        log.debug("observability.otel_disabled", reason="OTEL_EXPORTER_OTLP_ENDPOINT not set")
        return

    try:
        if not _OTEL_READY:
            _init_otel_providers(endpoint, settings.environment)
        if app is not None:
            _instrument_app(app)
    except Exception:
        # Misconfigured Alloy URL / missing optional packages must not block boot.
        log.exception("observability.otel_failed")


def _init_otel_providers(endpoint: str, environment: str) -> None:
    global _OTEL_READY

    from opentelemetry import metrics, trace
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.trace.sampling import ALWAYS_ON

    base = _otlp_base_url(endpoint)
    resource = Resource.create(
        {
            "service.name": "tcgscan-api",
            "service.namespace": "tcgscan",
            "deployment.environment": environment,
        }
    )

    # Low volume today — keep 100% traces in every environment.
    tracer_provider = TracerProvider(resource=resource, sampler=ALWAYS_ON)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{base}/v1/traces"))
    )
    trace.set_tracer_provider(tracer_provider)

    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=f"{base}/v1/metrics"),
        export_interval_millis=60_000,
    )
    metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[metric_reader]))

    _OTEL_READY = True
    log.info(
        "observability.otel_enabled",
        endpoint=base,
        sample_ratio=1.0,
        environment=environment,
    )


def _instrument_app(app: FastAPI) -> None:
    """Attach lightweight auto-instrumentation to the FastAPI app + httpx clients."""
    global _HTTPX_INSTRUMENTED

    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

    app_id = id(app)
    if app_id not in _INSTRUMENTED_APP_IDS:
        # Skip noisy probes; keep route/status/latency spans + metrics for the rest.
        FastAPIInstrumentor.instrument_app(
            app,
            excluded_urls="health,/v1/health,/favicon.ico",
        )
        _INSTRUMENTED_APP_IDS.add(app_id)

    if not _HTTPX_INSTRUMENTED:
        HTTPXClientInstrumentor().instrument()
        _HTTPX_INSTRUMENTED = True

    log.info("observability.otel_instrumented")
