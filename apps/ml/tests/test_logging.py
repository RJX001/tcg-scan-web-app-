"""Log severity coverage for ML Modal endpoints (M1 package)."""

from __future__ import annotations

import base64

import pytest
import structlog
from structlog.testing import capture_logs

import app as ml_app
from tcgscan_ml.grade import heuristic as heuristic_mod
from tcgscan_ml.grade.heuristic import grade_image_b64, grade_image_bytes


def _events(cap: list[dict[str, object]], event: str, *, level: str) -> list[dict[str, object]]:
    return [
        entry for entry in cap if entry.get("event") == event and entry.get("log_level") == level
    ]


@pytest.fixture(autouse=True)
def bind_structlog() -> None:
    ml_app.log = structlog.get_logger()
    heuristic_mod.log = structlog.get_logger()


def test_detect_logs_request_and_done() -> None:
    image_b64 = base64.b64encode(b"test-image").decode()
    with capture_logs() as cap:
        result = ml_app.detect(image_b64)

    assert result["image_b64_len"] == len(image_b64)
    assert len(_events(cap, "detect.request", level="info")) == 1
    done = _events(cap, "detect.done", level="info")
    assert len(done) == 1
    assert "duration_ms" in done[0]


def test_embed_logs_request_and_done() -> None:
    image_b64 = base64.b64encode(b"test-image").decode()
    with capture_logs() as cap:
        result = ml_app.embed(image_b64)

    assert result["embedding_dim"] == 1024
    assert len(_events(cap, "embed.request", level="info")) == 1
    done = _events(cap, "embed.done", level="info")
    assert len(done) == 1
    assert done[0]["embedding_dim"] == 1024


def test_ocr_logs_request_and_done() -> None:
    image_b64 = base64.b64encode(b"test-image").decode()
    with capture_logs() as cap:
        ml_app.ocr(image_b64)

    assert len(_events(cap, "ocr.request", level="info")) == 1
    assert len(_events(cap, "ocr.done", level="info")) == 1


def test_grade_endpoint_logs_request_and_done() -> None:
    image_b64 = base64.b64encode(b"test-image").decode()
    with capture_logs() as cap:
        result = ml_app.grade(image_b64)

    assert len(_events(cap, "grade.request", level="info")) == 1
    done = _events(cap, "grade.done", level="info")
    assert len(done) == 1
    assert done[0]["overall"] == result["overall"]


def test_embed_failed_logs_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(_: str) -> list[float]:
        raise RuntimeError("test failure")

    monkeypatch.setattr(ml_app, "_stub_embed_vector", boom)

    with capture_logs() as cap:
        with pytest.raises(RuntimeError, match="test failure"):
            ml_app.embed(base64.b64encode(b"test-image").decode())

    assert len(_events(cap, "embed.failed", level="error")) == 1


def test_grade_image_unreadable_logs_warning() -> None:
    with capture_logs() as cap:
        result = grade_image_bytes(b"not-a-valid-image")

    warnings = _events(cap, "grade.image_unreadable", level="warning")
    assert len(warnings) == 1
    assert "error" in warnings[0]
    assert result["confidence"] == 0.45


def test_grade_b64_fallback_logs_debug() -> None:
    with capture_logs() as cap:
        grade_image_b64("not-valid-base64!!!")

    assert len(_events(cap, "grade.b64_fallback", level="debug")) == 1
