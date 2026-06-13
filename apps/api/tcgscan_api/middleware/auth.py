"""Auth middleware — Clerk JWT or dev bypass."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from tcgscan_api.config import get_settings


@dataclass
class AuthUser:
    id: uuid.UUID
    clerk_id: str
    tier: str = "free"
    role: str = "user"
    email: str | None = None


async def _verify_clerk_bearer(token: str) -> tuple[str, str | None] | None:
    """Verify Clerk session JWT via Backend API. Returns (clerk_id, email)."""
    settings = get_settings()
    if not settings.clerk_secret_key:
        return None
    try:
        import httpx
        from clerk_backend_api import Clerk
        from clerk_backend_api.security.types import AuthenticateRequestOptions
    except ImportError:
        return None

    parties = [p.strip() for p in (settings.clerk_authorized_parties or "").split(",") if p.strip()]
    req = httpx.Request(
        method="GET",
        url="https://tcgscan.local/auth",
        headers=[("authorization", f"Bearer {token}")],
    )
    sdk = Clerk(bearer_auth=settings.clerk_secret_key)
    state = sdk.authenticate_request(
        req,
        AuthenticateRequestOptions(authorized_parties=parties or None),
    )
    if not state.is_signed_in or not state.payload:
        return None
    sub = state.payload.get("sub")
    if not sub:
        return None
    email = state.payload.get("email") or state.payload.get("primary_email_address")
    if isinstance(email, dict):
        email = email.get("email_address")
    return str(sub), str(email) if email else None


async def resolve_user(request: Request) -> AuthUser | None:
    settings = get_settings()
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:].strip()
        if token and settings.clerk_secret_key:
            verified = await _verify_clerk_bearer(token)
            if verified:
                clerk_id, email = verified
                return AuthUser(
                    id=uuid.uuid5(uuid.NAMESPACE_URL, clerk_id),
                    clerk_id=clerk_id,
                    email=email,
                )
        return None

    # Never allow dev-header auth in production — blocks X-Dev-User-Id bypass.
    if settings.environment == "production":
        return None

    if settings.dev_auth_enabled and not settings.clerk_secret_key:
        dev_id = request.headers.get("X-Dev-User-Id", "dev-user")
        return AuthUser(
            id=uuid.uuid5(uuid.NAMESPACE_DNS, dev_id),
            clerk_id=dev_id,
        )
    if settings.dev_auth_enabled and settings.clerk_secret_key:
        header_dev_id = request.headers.get("X-Dev-User-Id")
        if header_dev_id:
            return AuthUser(
                id=uuid.uuid5(uuid.NAMESPACE_DNS, header_dev_id),
                clerk_id=header_dev_id,
            )
    return None


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request.state.user = await resolve_user(request)
        return await call_next(request)
