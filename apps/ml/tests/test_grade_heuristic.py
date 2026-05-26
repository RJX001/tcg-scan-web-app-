from __future__ import annotations

import io

import pytest
from PIL import Image

from tcgscan_ml.grade.heuristic import grade_image_bytes
from tcgscan_ml.grade.psa import overall_to_psa_range


def _solid_jpeg(r: int, g: int, b: int) -> bytes:
    img = Image.new("RGB", (400, 560), (r, g, b))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_grade_returns_subgrades() -> None:
    out = grade_image_bytes(_solid_jpeg(180, 180, 180))
    assert out["overall"] is not None
    assert 1.0 <= out["overall"] <= 10.0
    assert out["centering"] is not None
    assert out["psa_label"].startswith("PSA")
    assert out["model"] == "heuristic-v0"


def test_psa_range_mapping() -> None:
    assert overall_to_psa_range(9.8) == (10, 10)
    assert overall_to_psa_range(8.9) == (8, 9)


def test_grade_is_deterministic() -> None:
    raw = _solid_jpeg(120, 140, 160)
    a = grade_image_bytes(raw)
    b = grade_image_bytes(raw)
    assert a == b
