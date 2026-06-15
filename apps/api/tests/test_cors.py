from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from tcgscan_api.cors import parse_cors_origins, wrap_with_cors
from tcgscan_api.db.models import UserRole
from tcgscan_api.db.session import get_session
from tcgscan_api.main import app, fastapi_app
from tcgscan_api.middleware.auth import AuthUser
from tcgscan_api.repositories.users import UsersRepo

CARDCHART_ORIGINS = [
    "https://cardchart.co.uk",
    "https://www.cardchart.co.uk",
]
CARDCHART_ORIGIN = "https://www.cardchart.co.uk"


def test_parse_cors_origins_strips_whitespace() -> None:
    raw = "https://cardchart.co.uk, https://www.cardchart.co.uk "
    assert parse_cors_origins(raw) == CARDCHART_ORIGINS


def test_parse_cors_origins_deduplicates() -> None:
    raw = "https://cardchart.co.uk,https://cardchart.co.uk"
    assert parse_cors_origins(raw) == ["https://cardchart.co.uk"]


@pytest_asyncio.fixture
async def cardchart_client(
    sqlite_session: object,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[AsyncClient]:
    monkeypatch.setenv("CORS_ORIGINS", ",".join(CARDCHART_ORIGINS))
    from tcgscan_api.config import get_settings

    get_settings.cache_clear()

    async def override_session() -> AsyncIterator[object]:
        yield sqlite_session

    fastapi_app.dependency_overrides[get_session] = override_session
    wrapped = wrap_with_cors(fastapi_app, CARDCHART_ORIGINS)
    transport = ASGITransport(app=wrapped)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    fastapi_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def api_client(sqlite_session: object) -> AsyncIterator[AsyncClient]:
    async def override_session() -> AsyncIterator[object]:
        yield sqlite_session

    fastapi_app.dependency_overrides[get_session] = override_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    fastapi_app.dependency_overrides.clear()


def _patch_auth(monkeypatch: pytest.MonkeyPatch, auth: AuthUser) -> None:
    import tcgscan_api.services.auth_ctx as auth_ctx

    async def fake_resolve(_session: object, _request: object) -> AuthUser:
        return auth

    monkeypatch.setattr(auth_ctx, "resolve_db_user", fake_resolve)


@pytest.mark.asyncio
async def test_options_preflight_me(cardchart_client: AsyncClient) -> None:
    response = await cardchart_client.options(
        "/v1/me",
        headers={
            "Origin": CARDCHART_ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )

    assert response.status_code in (200, 204)
    assert response.headers["access-control-allow-origin"] == CARDCHART_ORIGIN
    assert response.headers["access-control-allow-credentials"] == "true"


@pytest.mark.asyncio
async def test_options_preflight_market_fx(cardchart_client: AsyncClient) -> None:
    response = await cardchart_client.options(
        "/v1/market/fx",
        headers={
            "Origin": CARDCHART_ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "x-dev-user-id",
        },
    )

    assert response.status_code in (200, 204)
    assert response.headers["access-control-allow-origin"] == CARDCHART_ORIGIN
    assert response.headers["access-control-allow-credentials"] == "true"


@pytest.mark.asyncio
async def test_me_without_token_returns_401_with_cors(
    cardchart_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tcgscan_api.middleware import auth as auth_middleware

    async def no_user(_request: object) -> None:
        return None

    monkeypatch.setattr(auth_middleware, "resolve_user", no_user)

    response = await cardchart_client.get(
        "/v1/me",
        headers={"Origin": CARDCHART_ORIGIN},
    )

    assert response.status_code == 401
    assert response.headers["access-control-allow-origin"] == CARDCHART_ORIGIN
    assert response.headers["access-control-allow-credentials"] == "true"
    assert response.json()["detail"] == "Authentication required"


@pytest.mark.asyncio
async def test_me_returns_db_role_for_admin(
    api_client: AsyncClient,
    sqlite_session: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = await UsersRepo(sqlite_session).get_or_create(  # type: ignore[arg-type]
        supabase_user_id="admin-supabase-id",
        email="admin@example.com",
    )
    await UsersRepo(sqlite_session).set_role(user.id, UserRole.admin)  # type: ignore[arg-type]
    user = await UsersRepo(sqlite_session).get_by_id(user.id)  # type: ignore[arg-type]
    assert user is not None

    _patch_auth(
        monkeypatch,
        AuthUser(
            id=user.id,
            supabase_user_id=user.supabase_user_id or "admin-supabase-id",
            tier="free",
            role="admin",
            email=user.email,
        ),
    )

    r = await api_client.get("/v1/me", headers={"X-Dev-User-Id": "admin-supabase-id"})
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == str(user.id)
    assert body["email"] == "admin@example.com"
    assert body["role"] == "admin"
    assert body["tier"] == "free"
    assert body["supabase_user_id"] == "admin-supabase-id"


@pytest.mark.asyncio
async def test_me_requires_auth(api_client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from tcgscan_api.middleware import auth as auth_middleware

    async def no_user(_request: object) -> None:
        return None

    monkeypatch.setattr(auth_middleware, "resolve_user", no_user)

    r = await api_client.get("/v1/me")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_get_or_create_rejects_conflicting_email_identity(
    sqlite_session: object,
) -> None:
    repo = UsersRepo(sqlite_session)  # type: ignore[arg-type]
    await repo.get_or_create(supabase_user_id="user-a", email="dup@example.com")
    with pytest.raises(ValueError, match="another sign-in identity"):
        await repo.get_or_create(supabase_user_id="user-b", email="dup@example.com")
