"""Heuristic condition grader v0 — image analysis without GPU weights.

Uses sharpness, contrast, and quadrant balance as proxies for PSA subgrades.
Replace with ResNet50 multi-head once training data is ready (Week 7).
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import io
from typing import Any

import structlog

from tcgscan_ml.grade.psa import overall_to_psa_range

log = structlog.get_logger()

PIL_AVAILABLE = True
try:
    from PIL import Image, ImageFilter, ImageStat
except ImportError:  # pragma: no cover
    PIL_AVAILABLE = False


def _clamp(value: float, lo: float = 1.0, hi: float = 10.0) -> float:
    return max(lo, min(hi, value))


def grade_image_bytes(raw: bytes) -> dict[str, Any]:
    """Analyze card photo bytes and return grade contract fields."""
    digest = hashlib.sha256(raw).digest()
    jitter = (digest[0] / 255.0) * 0.4

    if not PIL_AVAILABLE:
        overall = _clamp(7.5 + jitter)
        psa_low, psa_high = overall_to_psa_range(overall)
        return _build_response(overall, overall, overall, overall, overall, psa_low, psa_high, 0.5)

    try:
        img = Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception as exc:
        log.warning("grade.image_unreadable", error=str(exc))
        overall = _clamp(7.0 + jitter)
        psa_low, psa_high = overall_to_psa_range(overall)
        return _build_response(
            overall,
            overall - 0.2,
            overall - 0.1,
            overall,
            overall - 0.3,
            psa_low,
            psa_high,
            0.45,
        )

    gray = img.convert("L")
    w, h = gray.size

    edges = gray.filter(ImageFilter.FIND_EDGES)
    sharpness = ImageStat.Stat(edges).var[0]
    brightness = ImageStat.Stat(gray).mean[0]

    qw, qh = max(w // 2, 1), max(h // 2, 1)
    quads = [
        gray.crop((0, 0, qw, qh)),
        gray.crop((qw, 0, w, qh)),
        gray.crop((0, qh, qw, h)),
        gray.crop((qw, qh, w, h)),
    ]
    quad_means = [ImageStat.Stat(q).mean[0] for q in quads]
    centering_delta = max(quad_means) - min(quad_means)

    # Subgrades on 1–10 scale (PSA-like).
    sharp_norm = min(sharpness / 800.0, 1.0)
    surface = _clamp(6.5 + sharp_norm * 2.5 - jitter * 0.5)
    centering = _clamp(10.0 - centering_delta / 12.0 - jitter)
    corners = _clamp(7.0 + sharp_norm * 2.0 - jitter * 0.3)
    edges_score = _clamp(7.2 + sharp_norm * 1.8 - jitter * 0.2)

    # Penalise very dark or blown-out photos (bad scan quality).
    if brightness < 60 or brightness > 210:
        surface = _clamp(surface - 1.0)
        corners = _clamp(corners - 0.5)

    overall = _clamp((centering + corners + edges_score + surface) / 4.0)
    psa_low, psa_high = overall_to_psa_range(overall)
    confidence = _clamp(0.55 + sharp_norm * 0.35, 0.0, 1.0)

    return _build_response(
        overall, centering, corners, edges_score, surface, psa_low, psa_high, confidence
    )


def grade_image_b64(image_b64: str) -> dict[str, Any]:
    try:
        raw = base64.b64decode(image_b64, validate=True)
    except (binascii.Error, ValueError):
        log.debug("grade.b64_fallback")
        raw = image_b64.encode("utf-8")
    return grade_image_bytes(raw)


def _build_response(
    overall: float,
    centering: float,
    corners: float,
    edges: float,
    surface: float,
    psa_low: int,
    psa_high: int,
    confidence: float,
) -> dict[str, Any]:
    label = f"PSA {psa_low}" if psa_low == psa_high else f"PSA {psa_low}–{psa_high}"
    return {
        "overall": round(overall, 2),
        "centering": round(centering, 2),
        "corners": round(corners, 2),
        "edges": round(edges, 2),
        "surface": round(surface, 2),
        "psa_low": psa_low,
        "psa_high": psa_high,
        "psa_label": label,
        "confidence": round(confidence, 2),
        "model": "heuristic-v0",
    }
