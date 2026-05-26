"""Modal deployment entry — detect, embed, ocr, grade."""

from __future__ import annotations

try:
    import modal

    modal_app: modal.App | None = modal.App("tcg-scan-ml")
    HAS_MODAL = True
except ImportError:
    modal_app = None
    HAS_MODAL = False

from tcgscan_ml.grade.heuristic import grade_image_b64


def _stub_embed_vector(image_b64: str, dim: int = 1024) -> list[float]:
    import hashlib

    digest = hashlib.sha256(image_b64.encode("utf-8")).digest()
    vec = [((digest[i % 32] / 255.0) * 2.0 - 1.0) for i in range(dim)]
    norm = sum(v * v for v in vec) ** 0.5 or 1.0
    return [v / norm for v in vec]


def detect(image_b64: str) -> dict[str, object]:
    return {"bboxes": [], "image_b64_len": len(image_b64)}


def embed(image_b64: str) -> dict[str, object]:
    vector = _stub_embed_vector(image_b64)
    return {"embedding_dim": 1024, "vector": vector}


def ocr(image_b64: str) -> dict[str, object]:
    return {"text": "", "image_b64_len": len(image_b64)}


def grade(image_b64: str) -> dict[str, object]:
    return grade_image_b64(image_b64)


if HAS_MODAL and modal_app is not None:
    detect_fn = modal_app.function()(detect)
    embed_fn = modal_app.function()(embed)
    ocr_fn = modal_app.function()(ocr)
    grade_fn = modal_app.function()(grade)
