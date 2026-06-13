from __future__ import annotations

import base64

import pytest
from httpx import ASGITransport, AsyncClient

from tcgscan_api.main import app
from tcgscan_api.services import scan as scan_mod
from tcgscan_api.services.scan import ScanInput, ScanResult, run_scan


@pytest.mark.asyncio
async def test_run_scan_falls_back_to_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_search(**_kwargs: object) -> list[object]:
        return []

    monkeypatch.setattr(scan_mod, "search_similar", fake_search)

    payload = ScanInput(image_b64=base64.b64encode(b"fake-image").decode())
    result = await run_scan(payload)
    assert isinstance(result, ScanResult)
    assert result.matches == []
    assert result.condition.overall is not None
    assert result.condition.psa_label is not None


@pytest.mark.asyncio
async def test_scan_endpoint_accepts_upload(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_search(**_kwargs: object) -> list[object]:
        return []

    async def noop_rate_limit(_request: object) -> None:
        return None

    monkeypatch.setattr(scan_mod, "search_similar", fake_search)
    monkeypatch.setattr("tcgscan_api.routes.scan.check_scan_rate_limit", noop_rate_limit)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(
            "/v1/scan",
            files={"image": ("card.jpg", b"\xff\xd8\xff\xd9", "image/jpeg")},
            data={"top_k": "3"},
            headers={"X-Dev-User-Id": "scan-test"},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "matches" in body
    assert "condition" in body
