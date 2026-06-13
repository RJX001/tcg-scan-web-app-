from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException

from tcgscan_api.middleware.auth import AuthUser
from tcgscan_api.services.roles import require_admin, require_owner, require_senior


def _user(role: str) -> AuthUser:
    return AuthUser(id=uuid.uuid4(), clerk_id="u", tier="free", role=role)


def test_require_admin_blocks_user() -> None:
    with pytest.raises(HTTPException) as exc:
        require_admin(_user("user"))
    assert exc.value.status_code == 403


@pytest.mark.parametrize("role", ["admin", "admin_senior", "owner"])
def test_require_admin_passes(role: str) -> None:
    require_admin(_user(role))


def test_require_senior_blocks_admin() -> None:
    with pytest.raises(HTTPException) as exc:
        require_senior(_user("admin"))
    assert exc.value.status_code == 403


@pytest.mark.parametrize("role", ["admin_senior", "owner"])
def test_require_senior_passes(role: str) -> None:
    require_senior(_user(role))


def test_require_owner_blocks_senior() -> None:
    with pytest.raises(HTTPException) as exc:
        require_owner(_user("admin_senior"))
    assert exc.value.status_code == 403


def test_require_owner_passes() -> None:
    require_owner(_user("owner"))
