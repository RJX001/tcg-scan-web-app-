"""Log severity coverage for billing webhooks and AppError handler."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
from structlog.testing import capture_logs

from tcgscan_api.config import Settings
from tcgscan_api.errors import AppError
from tcgscan_api.main import app_error_handler
from tcgscan_api.services import billing as billing_mod


def _request() -> Request:
    return Request({"type": "http", "method": "GET", "path": "/", "headers": []})


def _events(cap: list[dict[str, object]], event: str, *, level: str) -> list[dict[str, object]]:
    return [
        entry for entry in cap if entry.get("event") == event and entry.get("log_level") == level
    ]


class _InvalidSignatureStripe:
    class Webhook:
        @staticmethod
        def construct_event(
            _payload: bytes, _sig_header: str | None, _secret: str
        ) -> dict[str, object]:
            raise ValueError("Invalid signature")


@pytest.mark.asyncio
async def test_app_error_5xx_logs_api_app_error() -> None:
    with capture_logs() as cap:
        response = await app_error_handler(
            _request(), AppError("internal failure", status_code=500)
        )

    assert response.status_code == 500
    errors = _events(cap, "api.app_error", level="error")
    assert len(errors) == 1
    assert errors[0]["code"] == "AppError"
    assert errors[0]["status_code"] == 500
    assert errors[0]["message"] == "internal failure"


@pytest.mark.asyncio
async def test_app_error_4xx_does_not_log() -> None:
    with capture_logs() as cap:
        response = await app_error_handler(_request(), AppError("bad request", status_code=400))

    assert response.status_code == 400
    assert _events(cap, "api.app_error", level="error") == []


@pytest.mark.asyncio
async def test_stripe_webhook_invalid_signature_logs_warning(
    monkeypatch: pytest.MonkeyPatch,
    sqlite_session: AsyncSession,
) -> None:
    monkeypatch.setattr(
        billing_mod,
        "get_settings",
        lambda: Settings(
            _env_file=None,
            STRIPE_WEBHOOK_SECRET="whsec_test",
            STRIPE_SECRET_KEY="sk_test",
        ),
    )
    monkeypatch.setattr(billing_mod, "_stripe", lambda: _InvalidSignatureStripe())

    with capture_logs() as cap:
        with pytest.raises(AppError) as exc_info:
            await billing_mod.handle_stripe_webhook(sqlite_session, b"{}", "bad_sig")

    assert exc_info.value.status_code == 400
    warnings = _events(cap, "stripe.webhook_signature_invalid", level="warning")
    assert len(warnings) == 1
