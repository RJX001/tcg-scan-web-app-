"""Async client for the Modal ML endpoints (detect, embed, ocr, grade).

When the corresponding MODAL_*_URL env var is unset, returns a deterministic
local stub so the scan pipeline is end-to-end testable without GPU access.
"""

from __future__ import annotations

import hashlib
from typing import Any

import httpx
import structlog
from opentelemetry import metrics, trace

from tcgscan_api.config import get_settings

log = structlog.get_logger()

tracer = trace.get_tracer("tcgscan_api.ml")
meter = metrics.get_meter("tcgscan_api.ml")

ML_REQUESTS = meter.create_counter(
    "tcgscan.ml.requests",
    description="ML endpoint calls by mode",
)


def _stub_vector(image_b64: str, dim: int) -> list[float]:
    digest = hashlib.sha256(image_b64.encode("utf-8")).digest()
    vec = [(digest[i % 32] / 255.0) * 2.0 - 1.0 for i in range(dim)]
    norm = sum(v * v for v in vec) ** 0.5 or 1.0
    return [v / norm for v in vec]


class MLClient:
    def __init__(self, *, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(timeout=10.0)
        self._settings = get_settings()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _call(self, url: str | None, payload: dict[str, Any]) -> dict[str, Any] | None:
        if not url:
            return None
        try:
            r = await self._client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()
            return data if isinstance(data, dict) else None
        except (httpx.HTTPError, ValueError) as exc:
            log.warning("ml.error", url=url, error=str(exc))
            return None

    async def detect(self, image_b64: str) -> dict[str, Any]:
        url = self._settings.modal_detect_url
        with tracer.start_as_current_span("ml.detect") as span:
            span.set_attribute("tcgscan.ml.endpoint", "detect")
            if not url:
                span.set_attribute("tcgscan.ml.mode", "stub")
                ML_REQUESTS.add(1, {"tcgscan.ml.endpoint": "detect", "tcgscan.ml.mode": "stub"})
                return {"bboxes": [{"x": 0, "y": 0, "w": 1.0, "h": 1.0, "angle": 0.0}]}
            out = await self._call(url, {"image_b64": image_b64})
            if out:
                span.set_attribute("tcgscan.ml.mode", "live")
                ML_REQUESTS.add(1, {"tcgscan.ml.endpoint": "detect", "tcgscan.ml.mode": "live"})
                return out
            span.set_attribute("tcgscan.ml.mode", "fallback")
            ML_REQUESTS.add(1, {"tcgscan.ml.endpoint": "detect", "tcgscan.ml.mode": "fallback"})
            return {"bboxes": [{"x": 0, "y": 0, "w": 1.0, "h": 1.0, "angle": 0.0}]}

    async def embed(self, image_b64: str) -> list[float]:
        url = self._settings.modal_embed_url
        with tracer.start_as_current_span("ml.embed") as span:
            span.set_attribute("tcgscan.ml.endpoint", "embed")
            if not url:
                span.set_attribute("tcgscan.ml.mode", "stub")
                ML_REQUESTS.add(1, {"tcgscan.ml.endpoint": "embed", "tcgscan.ml.mode": "stub"})
                return _stub_vector(image_b64, self._settings.embedding_dim)
            out = await self._call(url, {"image_b64": image_b64})
            if (
                out
                and isinstance(out.get("vector"), list)
                and len(out["vector"]) == self._settings.embedding_dim
            ):
                span.set_attribute("tcgscan.ml.mode", "live")
                ML_REQUESTS.add(1, {"tcgscan.ml.endpoint": "embed", "tcgscan.ml.mode": "live"})
                return [float(x) for x in out["vector"]]
            span.set_attribute("tcgscan.ml.mode", "fallback")
            ML_REQUESTS.add(1, {"tcgscan.ml.endpoint": "embed", "tcgscan.ml.mode": "fallback"})
            return _stub_vector(image_b64, self._settings.embedding_dim)

    async def ocr(self, image_b64: str) -> dict[str, Any]:
        url = self._settings.modal_ocr_url
        with tracer.start_as_current_span("ml.ocr") as span:
            span.set_attribute("tcgscan.ml.endpoint", "ocr")
            if not url:
                span.set_attribute("tcgscan.ml.mode", "stub")
                ML_REQUESTS.add(1, {"tcgscan.ml.endpoint": "ocr", "tcgscan.ml.mode": "stub"})
                return {"text": "", "fields": {}}
            out = await self._call(url, {"image_b64": image_b64})
            if out:
                span.set_attribute("tcgscan.ml.mode", "live")
                ML_REQUESTS.add(1, {"tcgscan.ml.endpoint": "ocr", "tcgscan.ml.mode": "live"})
                return out
            span.set_attribute("tcgscan.ml.mode", "fallback")
            ML_REQUESTS.add(1, {"tcgscan.ml.endpoint": "ocr", "tcgscan.ml.mode": "fallback"})
            return {"text": "", "fields": {}}

    async def grade(self, image_b64: str) -> dict[str, Any]:
        url = self._settings.modal_grade_url
        with tracer.start_as_current_span("ml.grade") as span:
            span.set_attribute("tcgscan.ml.endpoint", "grade")
            if not url:
                span.set_attribute("tcgscan.ml.mode", "stub")
                ML_REQUESTS.add(1, {"tcgscan.ml.endpoint": "grade", "tcgscan.ml.mode": "stub"})
                from tcgscan_ml.grade.heuristic import grade_image_b64

                return grade_image_b64(image_b64)
            out = await self._call(url, {"image_b64": image_b64})
            if out and out.get("overall") is not None:
                span.set_attribute("tcgscan.ml.mode", "live")
                ML_REQUESTS.add(1, {"tcgscan.ml.endpoint": "grade", "tcgscan.ml.mode": "live"})
                return out
            span.set_attribute("tcgscan.ml.mode", "fallback")
            ML_REQUESTS.add(1, {"tcgscan.ml.endpoint": "grade", "tcgscan.ml.mode": "fallback"})
            from tcgscan_ml.grade.heuristic import grade_image_b64

            return grade_image_b64(image_b64)
