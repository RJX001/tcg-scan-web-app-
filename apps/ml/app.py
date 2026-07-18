"""Modal deployment entry — detect, embed, ocr, grade."""

from __future__ import annotations

import time

import structlog

try:
    import modal

    modal_app: modal.App | None = modal.App("tcg-scan-ml")
    HAS_MODAL = True
except ImportError:
    modal_app = None
    HAS_MODAL = False

from tcgscan_ml.grade.heuristic import grade_image_b64

log = structlog.get_logger()


def _stub_embed_vector(image_b64: str, dim: int = 1024) -> list[float]:
    import hashlib

    digest = hashlib.sha256(image_b64.encode("utf-8")).digest()
    vec = [((digest[i % 32] / 255.0) * 2.0 - 1.0) for i in range(dim)]
    norm = sum(v * v for v in vec) ** 0.5 or 1.0
    return [v / norm for v in vec]


def detect(image_b64: str) -> dict[str, object]:
    """Return full-frame bbox when no YOLO model is loaded (local dev)."""
    started = time.perf_counter()
    log.info("detect.request", image_b64_len=len(image_b64))
    try:
        result: dict[str, object] = {
            "bboxes": [{"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0, "angle": 0.0}],
            "image_b64_len": len(image_b64),
        }
        log.info(
            "detect.done",
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
            bbox_count=1,
        )
        return result
    except Exception:
        log.exception("detect.failed")
        raise


def embed(image_b64: str) -> dict[str, object]:
    started = time.perf_counter()
    log.info("embed.request", image_b64_len=len(image_b64))
    try:
        vector = _stub_embed_vector(image_b64)
        result: dict[str, object] = {"embedding_dim": 1024, "vector": vector}
        log.info(
            "embed.done",
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
            embedding_dim=1024,
        )
        return result
    except Exception:
        log.exception("embed.failed")
        raise


def ocr(image_b64: str) -> dict[str, object]:
    """Stub OCR — returns empty text; wire PaddleOCR in production Modal deploy."""
    started = time.perf_counter()
    log.info("ocr.request", image_b64_len=len(image_b64))
    try:
        result: dict[str, object] = {
            "text": "",
            "fields": {"name": None, "number": None, "set": None},
        }
        log.info(
            "ocr.done",
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
        )
        return result
    except Exception:
        log.exception("ocr.failed")
        raise


def grade(image_b64: str) -> dict[str, object]:
    started = time.perf_counter()
    log.info("grade.request", image_b64_len=len(image_b64))
    try:
        result = grade_image_b64(image_b64)
        log.info(
            "grade.done",
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
            overall=result.get("overall"),
            confidence=result.get("confidence"),
        )
        return result
    except Exception:
        log.exception("grade.failed")
        raise


if HAS_MODAL and modal_app is not None:
    detect_fn = modal_app.function()(detect)
    embed_fn = modal_app.function()(embed)
    ocr_fn = modal_app.function()(ocr)
    grade_fn = modal_app.function()(grade)
