from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from tcgscan_api.db.models import UserRole
from tcgscan_api.db.session import get_session
from tcgscan_api.main import app
from tcgscan_api.middleware.auth import AuthUser
from tcgscan_api.repositories.users import UsersRepo


@pytest_asyncio.fixture
async def api_client(sqlite_session: object) -> AsyncIterator[AsyncClient]:
    async def override_session() -> AsyncIterator[object]:
        yield sqlite_session

    app.dependency_overrides[get_session] = override_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


def _patch_auth(monkeypatch: pytest.MonkeyPatch, auth: AuthUser) -> None:
    import tcgscan_api.services.auth_ctx as auth_ctx

    async def fake_resolve(_session: object, _request: object) -> AuthUser:
        return auth

    monkeypatch.setattr(auth_ctx, "resolve_db_user", fake_resolve)


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
