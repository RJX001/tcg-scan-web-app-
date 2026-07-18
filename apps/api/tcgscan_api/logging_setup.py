"""structlog → stdlib logging bridge (JSON stdout + OTEL LogHandler correlation)."""

from __future__ import annotations

import logging
import sys
from typing import Any, MutableMapping

import structlog

_LOGGING_CONFIGURED = False


def _inject_trace_context(
    _logger: object,
    _method_name: str,
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    """Inject OTEL trace_id / span_id / trace_flags (hex) when a valid span is active."""
    from opentelemetry import trace

    span = trace.get_current_span()
    span_context = span.get_span_context()
    if span_context.is_valid:
        event_dict["trace_id"] = format(span_context.trace_id, "032x")
        event_dict["span_id"] = format(span_context.span_id, "016x")
        event_dict["trace_flags"] = format(int(span_context.trace_flags), "02x")
    return event_dict


def configure_logging() -> None:
    """Configure structlog + stdlib root logger for JSON stdout.

    Routes structlog through stdlib so the OTEL ``LoggingHandler`` (attached later
    by ``init_observability``) sees all app logs. Idempotent — safe to call twice.
    """
    global _LOGGING_CONFIGURED
    if _LOGGING_CONFIGURED:
        return

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _inject_trace_context,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ]

    structlog.configure(
        processors=shared_processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        # False so monorepo tests (and capture_logs) can reconfigure processors;
        # cached BoundLoggers ignore later structlog.configure() calls.
        cache_logger_on_first_use=False,
    )

    foreign_pre_chain: list[structlog.types.Processor] = [
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=foreign_pre_chain,
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)

    _LOGGING_CONFIGURED = True
