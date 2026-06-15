"""Tier gating tests."""

from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException

from tcgscan_api.middleware.auth import AuthUser
from tcgscan_api.services.tier import require_pro


def test_alerts_require_pro() -> None:
    user = AuthUser(id=uuid.uuid4(), supabase_user_id="free-user", tier="free")
    with pytest.raises(HTTPException) as exc:
        require_pro(user, feature="Price alerts")
    assert exc.value.status_code == 403
    assert "Pro" in exc.value.detail


def test_pro_user_passes_tier_check() -> None:
    user = AuthUser(id=uuid.uuid4(), supabase_user_id="pro-user", tier="pro")
    require_pro(user, feature="Price alerts")
