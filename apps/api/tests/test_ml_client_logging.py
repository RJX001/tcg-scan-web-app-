"""Log severity coverage for MLClient fallback paths."""

from __future__ import annotations

import base64

import httpx
import pytest
import respx
import structlog
from httpx import Response
from structlog.testing import capture_logs

from tcgscan_api.config import Settings
from tcgscan_api.services import ml_client as ml_mod


@pytest.fixture
def fake_image_b64() -> str:
    return base64.b64encode(b"fake-image-for-ml-logging").decode()


@pytest.mark.asyncio
@respx.mock
async def test_ml_error_logged_when_configured_url_fails(
    fake_image_b64: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    detect_url = "http://ml.test/detect"
    monkeypatch.setattr(
        ml_mod,
        "get_settings",
        lambda: Settings(_env_file=None, MODAL_DETECT_URL=detect_url),
    )
    respx.post(detect_url).mock(return_value=Response(500))

    with capture_logs() as logs:
        ml_mod.log = structlog.get_logger()
        client = ml_mod.MLClient()
        try:
            await client.detect(fake_image_b64)
        finally:
            await client.aclose()

    error_logs = [entry for entry in logs if entry.get("event") == "ml.error"]
    assert len(error_logs) == 1
    assert error_logs[0]["log_level"] == "error"
    assert error_logs[0]["endpoint"] == "detect"
    assert error_logs[0]["url"] == detect_url
    assert "error" in error_logs[0]


@pytest.mark.asyncio
async def test_ml_stub_mode_emits_no_error_log(
    fake_image_b64: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        ml_mod,
        "get_settings",
        lambda: Settings(_env_file=None),
    )

    with capture_logs() as logs:
        ml_mod.log = structlog.get_logger()
        client = ml_mod.MLClient()
        try:
            await client.detect(fake_image_b64)
        finally:
            await client.aclose()

    assert not any(entry.get("event") == "ml.error" for entry in logs)


@pytest.mark.asyncio
async def test_ml_error_logged_for_unusable_payload(
    fake_image_b64: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    embed_url = "http://ml.test/embed"
    monkeypatch.setattr(
        ml_mod,
        "get_settings",
        lambda: Settings(_env_file=None, MODAL_EMBED_URL=embed_url),
    )

    async def bad_call(_url: str, _payload: dict[str, object]) -> dict[str, object]:
        return {"vector": [0.1, 0.2]}

    with capture_logs() as logs:
        ml_mod.log = structlog.get_logger()
        client = ml_mod.MLClient()
        monkeypatch.setattr(client, "_call", bad_call)
        try:
            await client.embed(fake_image_b64)
        finally:
            await client.aclose()

    error_logs = [entry for entry in logs if entry.get("event") == "ml.error"]
    assert len(error_logs) == 1
    assert error_logs[0]["log_level"] == "error"
    assert error_logs[0]["endpoint"] == "embed"
    assert error_logs[0]["url"] == embed_url
    assert error_logs[0]["error"] == "invalid or missing embed vector"


@pytest.mark.asyncio
@respx.mock
async def test_ml_error_logged_on_connection_failure(
    fake_image_b64: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ocr_url = "http://ml.test/ocr"
    monkeypatch.setattr(
        ml_mod,
        "get_settings",
        lambda: Settings(_env_file=None, MODAL_OCR_URL=ocr_url),
    )
    respx.post(ocr_url).mock(side_effect=httpx.ConnectError("connection refused"))

    with capture_logs() as logs:
        ml_mod.log = structlog.get_logger()
        client = ml_mod.MLClient()
        try:
            await client.ocr(fake_image_b64)
        finally:
            await client.aclose()

    error_logs = [entry for entry in logs if entry.get("event") == "ml.error"]
    assert len(error_logs) == 1
    assert error_logs[0]["log_level"] == "error"
    assert error_logs[0]["endpoint"] == "ocr"
    assert error_logs[0]["url"] == ocr_url
