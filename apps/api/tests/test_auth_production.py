"""Production auth hardening — dev header bypass must be disabled."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from tcgscan_api.config import get_settings
from tcgscan_api.main import app
from tcgscan_api.middleware.auth import resolve_user


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_dev_user_header_rejected_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    get_settings.cache_clear()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/v1/health", headers={"X-Dev-User-Id": "attacker"})
    assert r.status_code == 200

    from starlette.requests import Request

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(b"x-dev-user-id", b"attacker")],
        "query_string": b"",
    }
    request = Request(scope)
    user = await resolve_user(request)
    assert user is None


@pytest.mark.asyncio
async def test_dev_user_header_allowed_in_development(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("DEV_AUTH_ENABLED", "true")
    monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
    monkeypatch.delenv("SUPABASE_JWKS_URL", raising=False)
    get_settings.cache_clear()

    from starlette.requests import Request

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(b"x-dev-user-id", b"dev-user")],
        "query_string": b"",
    }
    request = Request(scope)
    user = await resolve_user(request)
    assert user is not None
    assert user.supabase_user_id == "dev-user"


@pytest.mark.asyncio
async def test_supabase_bearer_token_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    import jwt
    from datetime import UTC, datetime, timedelta

    secret = "test-secret-for-jwt"
    url = "https://testproject.supabase.co"
    monkeypatch.setenv("SUPABASE_URL", url)
    monkeypatch.setenv("SUPABASE_JWT_SECRET", secret)
    monkeypatch.delenv("SUPABASE_JWKS_URL", raising=False)
    get_settings.cache_clear()

    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "email": "user@example.com",
            "aud": "authenticated",
            "iss": f"{url}/auth/v1",
            "exp": now + timedelta(hours=1),
        },
        secret,
        algorithm="HS256",
    )

    from starlette.requests import Request

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(b"authorization", f"Bearer {token}".encode())],
        "query_string": b"",
    }
    request = Request(scope)
    user = await resolve_user(request)
    assert user is not None
    assert user.supabase_user_id == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    assert user.email == "user@example.com"
