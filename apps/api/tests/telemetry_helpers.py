"""Shared OTEL test helpers (spans + metric capture doubles)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


def _is_sdk_tracer_provider(provider: object) -> bool:
    return isinstance(provider, TracerProvider)


@dataclass
class MetricCapture:
    """Captures histogram.record / counter.add calls."""

    histograms: list[tuple[float, dict[str, Any]]] = field(default_factory=list)
    counters: list[tuple[int, dict[str, Any]]] = field(default_factory=list)

    def record(self, value: float, attrs: dict[str, Any] | None = None) -> None:
        self.histograms.append((value, dict(attrs or {})))

    def add(self, value: int, attrs: dict[str, Any] | None = None) -> None:
        self.counters.append((value, dict(attrs or {})))


def span_names(exporter: InMemorySpanExporter) -> list[str]:
    return [span.name for span in exporter.get_finished_spans()]


def span_by_name(exporter: InMemorySpanExporter, name: str) -> Any:
    for span in exporter.get_finished_spans():
        if span.name == name:
            return span
    raise AssertionError(f"span {name!r} not found; have {span_names(exporter)!r}")


def span_attr(span: object, key: str) -> Any:
    attrs = getattr(span, "attributes", None) or {}
    if key not in attrs:
        raise AssertionError(f"attribute {key!r} missing on span; have {list(attrs)!r}")
    return attrs[key]
