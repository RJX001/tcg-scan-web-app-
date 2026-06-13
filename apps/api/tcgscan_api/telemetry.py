"""Optional Sentry + OpenTelemetry bootstrap."""

from __future__ import annotations

import structlog

from tcgscan_api.config import get_settings

log = structlog.get_logger()


def init_observability() -> None:
    settings = get_settings()
    if settings.sentry_dsn_api:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.fastapi import FastApiIntegration

            sentry_sdk.init(
                dsn=settings.sentry_dsn_api,
                integrations=[FastApiIntegration()],
                traces_sample_rate=0.1,
                environment="development",
            )
            log.info("observability.sentry_enabled")
        except ImportError:
            log.warning("observability.sentry_skipped", reason="sentry-sdk not installed")

    if settings.otel_exporter_otlp_endpoint:
        try:
            from opentelemetry import trace
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor

            provider = TracerProvider(resource=Resource.create({"service.name": "tcgscan-api"}))
            provider.add_span_processor(
                BatchSpanProcessor(
                    OTLPSpanExporter(endpoint=f"{settings.otel_exporter_otlp_endpoint}/v1/traces")
                )
            )
            trace.set_tracer_provider(provider)
            log.info("observability.otel_enabled")
        except ImportError:
            log.warning("observability.otel_skipped", reason="opentelemetry packages not installed")
