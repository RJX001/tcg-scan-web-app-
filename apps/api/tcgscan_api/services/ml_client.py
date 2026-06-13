"""Async client for the Modal ML endpoints (detect, embed, ocr, grade).

When the corresponding MODAL_*_URL env var is unset, returns a deterministic
local stub so the scan pipeline is end-to-end testable without GPU access.
"""

from __future__ import annotations

import hashlib
from typing import Any

import httpx
import structlog

from tcgscan_api.config import get_settings

log = structlog.get_logger()


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
        out = await self._call(self._settings.modal_detect_url, {"image_b64": image_b64})
        return out or {"bboxes": [{"x": 0, "y": 0, "w": 1.0, "h": 1.0, "angle": 0.0}]}

    async def embed(self, image_b64: str) -> list[float]:
        out = await self._call(self._settings.modal_embed_url, {"image_b64": image_b64})
        if (
            out
            and isinstance(out.get("vector"), list)
            and len(out["vector"]) == self._settings.embedding_dim
        ):
            return [float(x) for x in out["vector"]]
        return _stub_vector(image_b64, self._settings.embedding_dim)

    async def ocr(self, image_b64: str) -> dict[str, Any]:
        out = await self._call(self._settings.modal_ocr_url, {"image_b64": image_b64})
        return out or {"text": "", "fields": {}}

    async def grade(self, image_b64: str) -> dict[str, Any]:
        out = await self._call(self._settings.modal_grade_url, {"image_b64": image_b64})
        if out and out.get("overall") is not None:
            return out
        from tcgscan_ml.grade.heuristic import grade_image_b64

        return grade_image_b64(image_b64)
