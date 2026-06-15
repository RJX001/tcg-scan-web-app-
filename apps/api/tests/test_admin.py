from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from tcgscan_api.config import get_settings
from tcgscan_api.db.models import User, UserRole, UserTier
from tcgscan_api.db.session import get_session
from tcgscan_api.main import app, fastapi_app
from tcgscan_api.middleware.auth import AuthUser
from tcgscan_api.repositories.users import UsersRepo


@pytest_asyncio.fixture
async def api_client(sqlite_session: object) -> AsyncIterator[AsyncClient]:
    async def override_session() -> AsyncIterator[object]:
        yield sqlite_session

    fastapi_app.dependency_overrides[get_session] = override_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    fastapi_app.dependency_overrides.clear()


async def _make_user(
    session: object,
    *,
    supabase_user_id: str,
    role: UserRole = UserRole.user,
    email: str | None = None,
    account_number: str | None = None,
) -> User:
    repo = UsersRepo(session)  # type: ignore[arg-type]
    user = await repo.get_or_create(supabase_user_id=supabase_user_id, email=email)
    if role != UserRole.user:
        await repo.set_role(user.id, role)
        user = await repo.get_by_id(user.id)
        assert user is not None
    if account_number is not None:
        await repo.set_account_number(user.id, account_number)
        user = await repo.get_by_id(user.id)
        assert user is not None
    return user


def _patch_auth(monkeypatch: pytest.MonkeyPatch, auth: AuthUser) -> None:
    import tcgscan_api.services.auth_ctx as auth_ctx

    async def fake_resolve(_session: object, _request: object) -> AuthUser:
        return auth

    monkeypatch.setattr(auth_ctx, "resolve_db_user", fake_resolve)


@pytest.mark.asyncio
async def test_owner_email_bootstrap(
    sqlite_session: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("OWNER_EMAIL", "owner@example.com")
    get_settings.cache_clear()

    user = await UsersRepo(sqlite_session).get_or_create(  # type: ignore[arg-type]
        supabase_user_id="owner-user", email="owner@example.com"
    )
    assert user.role == UserRole.owner
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_new_user_gets_account_number_starting_at_10(
    sqlite_session: object,
) -> None:
    user = await UsersRepo(sqlite_session).get_or_create(supabase_user_id="acct-user")  # type: ignore[arg-type]
    assert user.account_seq == 10
    assert user.account_number == "000010"


@pytest.mark.asyncio
async def test_admin_overview_forbidden_for_user(
    api_client: AsyncClient, sqlite_session: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = await _make_user(sqlite_session, supabase_user_id="plain-user", role=UserRole.user)
    _patch_auth(
        monkeypatch,
        AuthUser(id=user.id, supabase_user_id=user.supabase_user_id, tier="free", role="user"),
    )

    r = await api_client.get("/v1/admin/overview", headers={"X-Dev-User-Id": "plain-user"})
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_admin_overview_ok_for_admin(
    api_client: AsyncClient, sqlite_session: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = await _make_user(sqlite_session, supabase_user_id="admin-user", role=UserRole.admin)
    _patch_auth(
        monkeypatch,
        AuthUser(id=user.id, supabase_user_id=user.supabase_user_id, tier="free", role="admin"),
    )

    r = await api_client.get("/v1/admin/overview", headers={"X-Dev-User-Id": "admin-user"})
    assert r.status_code == 200
    body = r.json()
    assert "total_users" in body


@pytest.mark.asyncio
async def test_set_tier_senior_only(
    api_client: AsyncClient, sqlite_session: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = await _make_user(sqlite_session, supabase_user_id="target-user")
    admin = await _make_user(sqlite_session, supabase_user_id="plain-admin", role=UserRole.admin)
    senior = await _make_user(
        sqlite_session, supabase_user_id="senior-admin", role=UserRole.admin_senior
    )

    _patch_auth(
        monkeypatch,
        AuthUser(id=admin.id, supabase_user_id=admin.supabase_user_id, tier="free", role="admin"),
    )
    r_forbidden = await api_client.post(
        f"/v1/admin/users/{target.id}/tier",
        json={"tier": "pro"},
        headers={"X-Dev-User-Id": "plain-admin"},
    )

    _patch_auth(
        monkeypatch,
        AuthUser(
            id=senior.id, supabase_user_id=senior.supabase_user_id, tier="free", role="admin_senior"
        ),
    )
    r_ok = await api_client.post(
        f"/v1/admin/users/{target.id}/tier",
        json={"tier": "pro"},
        headers={"X-Dev-User-Id": "senior-admin"},
    )

    assert r_forbidden.status_code == 403
    assert r_ok.status_code == 200
    updated = await UsersRepo(sqlite_session).get_by_id(target.id)  # type: ignore[arg-type]
    assert updated is not None
    assert updated.tier == UserTier.pro


@pytest.mark.asyncio
async def test_set_role_owner_only(
    api_client: AsyncClient, sqlite_session: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = await _make_user(sqlite_session, supabase_user_id="role-target")
    senior = await _make_user(sqlite_session, supabase_user_id="senior", role=UserRole.admin_senior)
    owner = await _make_user(sqlite_session, supabase_user_id="owner", role=UserRole.owner)

    _patch_auth(
        monkeypatch,
        AuthUser(
            id=senior.id, supabase_user_id=senior.supabase_user_id, tier="free", role="admin_senior"
        ),
    )
    r_forbidden = await api_client.post(
        f"/v1/admin/users/{target.id}/role",
        json={"role": "admin"},
        headers={"X-Dev-User-Id": "senior"},
    )

    _patch_auth(
        monkeypatch,
        AuthUser(id=owner.id, supabase_user_id=owner.supabase_user_id, tier="free", role="owner"),
    )
    r_ok = await api_client.post(
        f"/v1/admin/users/{target.id}/role",
        json={"role": "admin"},
        headers={"X-Dev-User-Id": "owner"},
    )

    assert r_forbidden.status_code == 403
    assert r_ok.status_code == 200


@pytest.mark.asyncio
async def test_owner_cannot_demote_self(
    api_client: AsyncClient, sqlite_session: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner = await _make_user(sqlite_session, supabase_user_id="owner-self", role=UserRole.owner)
    _patch_auth(
        monkeypatch,
        AuthUser(id=owner.id, supabase_user_id=owner.supabase_user_id, tier="free", role="owner"),
    )

    r = await api_client.post(
        f"/v1/admin/users/{owner.id}/role",
        json={"role": "user"},
        headers={"X-Dev-User-Id": "owner-self"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_duplicate_account_number_409(
    api_client: AsyncClient, sqlite_session: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _make_user(sqlite_session, supabase_user_id="u1", account_number="000001")
    target = await _make_user(sqlite_session, supabase_user_id="u2")
    owner = await _make_user(sqlite_session, supabase_user_id="owner-dup", role=UserRole.owner)
    _patch_auth(
        monkeypatch,
        AuthUser(id=owner.id, supabase_user_id=owner.supabase_user_id, tier="free", role="owner"),
    )

    r = await api_client.post(
        f"/v1/admin/users/{target.id}/account-number",
        json={"account_number": "000001"},
        headers={"X-Dev-User-Id": "owner-dup"},
    )
    assert r.status_code == 409
