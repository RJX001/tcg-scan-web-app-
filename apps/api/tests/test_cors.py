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


@pytest.mark.asyncio
async def test_owner_email_relinks_supabase_id_without_duplicate(
    sqlite_session: object,
) -> None:
    """Migrated owner row keeps role/billing; current Supabase SID is attached."""
    from tcgscan_api.db.models import UserRole, UserTier
    from tcgscan_api.repositories.users import CANONICAL_OWNER_EMAIL

    repo = UsersRepo(sqlite_session)  # type: ignore[arg-type]
    owner = await repo.get_or_create(
        supabase_user_id="legacy-clerk-or-old-supabase",
        email=CANONICAL_OWNER_EMAIL,
    )
    owner.role = UserRole.owner
    owner.tier = UserTier.pro
    owner.stripe_customer_id = "cus_owner_keep"
    await sqlite_session.commit()
    owner_id = owner.id
    stripe_id = owner.stripe_customer_id
    account_number = owner.account_number

    relinked = await repo.get_or_create(
        supabase_user_id="current-supabase-sid",
        email=CANONICAL_OWNER_EMAIL,
    )
    assert relinked.id == owner_id
    assert relinked.supabase_user_id == "current-supabase-sid"
    assert relinked.role == UserRole.owner
    assert relinked.stripe_customer_id == stripe_id
    assert relinked.account_number == account_number

    # No second owner row for the same email.
    matches = await repo._users_by_email(CANONICAL_OWNER_EMAIL)
    assert len([u for u in matches if u.role == UserRole.owner]) == 1


@pytest.mark.asyncio
async def test_owner_email_prefers_admin_row_over_empty_duplicate(
    sqlite_session: object,
) -> None:
    from datetime import datetime, timedelta

    from tcgscan_api.db.models import User, UserRole, UserTier
    from tcgscan_api.repositories.users import CANONICAL_OWNER_EMAIL

    repo = UsersRepo(sqlite_session)  # type: ignore[arg-type]
    empty = User(
        supabase_user_id=None,
        email=CANONICAL_OWNER_EMAIL,
        tier=UserTier.free,
        role=UserRole.user,
        account_seq=11,
        account_number="000011",
        created_at=datetime.now() - timedelta(days=1),
    )
    owner = User(
        supabase_user_id="stale-sid",
        email=CANONICAL_OWNER_EMAIL,
        tier=UserTier.pro,
        role=UserRole.owner,
        account_seq=12,
        account_number="000012",
        stripe_customer_id="cus_canonical",
        created_at=datetime.now() - timedelta(days=30),
    )
    sqlite_session.add_all([empty, owner])
    await sqlite_session.commit()

    result = await repo.get_or_create(
        supabase_user_id="fresh-supabase-sid",
        email=CANONICAL_OWNER_EMAIL,
    )
    assert result.id == owner.id
    assert result.supabase_user_id == "fresh-supabase-sid"
    assert result.stripe_customer_id == "cus_canonical"
    assert result.role == UserRole.owner


@pytest.mark.asyncio
async def test_owner_email_reclaims_sid_from_blank_duplicate_row(
    sqlite_session: object,
) -> None:
    from tcgscan_api.db.models import User, UserRole, UserTier
    from tcgscan_api.repositories.users import CANONICAL_OWNER_EMAIL

    repo = UsersRepo(sqlite_session)  # type: ignore[arg-type]
    blank = User(
        supabase_user_id="fresh-supabase-sid",
        email=None,
        tier=UserTier.free,
        role=UserRole.user,
        account_seq=13,
        account_number="000013",
    )
    owner = User(
        supabase_user_id="stale-sid",
        email=CANONICAL_OWNER_EMAIL,
        tier=UserTier.pro,
        role=UserRole.owner,
        account_seq=14,
        account_number="000014",
        stripe_customer_id="cus_keep",
    )
    sqlite_session.add_all([blank, owner])
    await sqlite_session.commit()
    owner_id = owner.id

    result = await repo.get_or_create(
        supabase_user_id="fresh-supabase-sid",
        email=CANONICAL_OWNER_EMAIL,
    )
    assert result.id == owner_id
    assert result.supabase_user_id == "fresh-supabase-sid"
    assert result.stripe_customer_id == "cus_keep"
    await sqlite_session.refresh(blank)
    assert blank.supabase_user_id is None
