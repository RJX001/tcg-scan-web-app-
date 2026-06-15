from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from httpx import ASGITransport, AsyncClient

from tcgscan_api.cors import CORS_ALLOW_HEADERS, CORS_ALLOW_METHODS, parse_cors_origins


def test_parse_cors_origins_strips_whitespace() -> None:
    raw = "https://cardchart.co.uk, https://www.cardchart.co.uk "
    assert parse_cors_origins(raw) == [
        "https://cardchart.co.uk",
        "https://www.cardchart.co.uk",
    ]


def test_parse_cors_origins_deduplicates() -> None:
    raw = "https://cardchart.co.uk,https://cardchart.co.uk"
    assert parse_cors_origins(raw) == ["https://cardchart.co.uk"]


@pytest.mark.asyncio
async def test_options_preflight_me_allows_authorization_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "CORS_ORIGINS",
        "https://cardchart.co.uk,https://www.cardchart.co.uk",
    )

    from tcgscan_api.config import get_settings

    get_settings.cache_clear()

    test_app = FastAPI()
    origins = parse_cors_origins(get_settings().cors_origins)
    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=CORS_ALLOW_METHODS,
        allow_headers=CORS_ALLOW_HEADERS,
    )

    @test_app.get("/v1/me")
    async def me() -> dict[str, str]:
        return {"ok": "true"}

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.options(
            "/v1/me",
            headers={
                "Origin": "https://www.cardchart.co.uk",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://www.cardchart.co.uk"
    assert response.headers["access-control-allow-credentials"] == "true"
    allow_headers = response.headers.get("access-control-allow-headers", "").lower()
    assert "authorization" in allow_headers
