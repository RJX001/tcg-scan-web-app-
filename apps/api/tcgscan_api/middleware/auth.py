"""Auth middleware — Supabase JWT (primary), Clerk JWT fallback, or dev bypass."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import jwt
from fastapi import Request
from jwt import PyJWKClient
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from tcgscan_api.config import get_settings

_jwk_client: PyJWKClient | None = None


@dataclass
class AuthUser:
    id: uuid.UUID
    clerk_id: str = ""
    supabase_user_id: str | None = None
    tier: str = "free"
    role: str = "user"
    email: str | None = None


def _supabase_issuer() -> str | None:
    settings = get_settings()
    if not settings.supabase_url:
        return None
    return f"{settings.supabase_url.rstrip('/')}/auth/v1"


def _verify_supabase_bearer(token: str) -> tuple[str, str | None] | None:
    """Verify Supabase access JWT. Returns (supabase_user_id, email)."""
    settings = get_settings()
    issuer = _supabase_issuer()
    if not issuer:
        return None

    try:
        if settings.supabase_jwks_url:
            global _jwk_client
            if _jwk_client is None:
                _jwk_client = PyJWKClient(settings.supabase_jwks_url, cache_keys=True)
            signing_key = _jwk_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["HS256", "RS256", "ES256"],
                audience="authenticated",
                issuer=issuer,
                options={"require": ["exp", "sub"]},
            )
        elif settings.supabase_jwt_secret:
            payload = jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
                issuer=issuer,
                options={"require": ["exp", "sub"]},
            )
        else:
            return None
    except jwt.PyJWTError:
        return None

    sub = payload.get("sub")
    if not sub:
        return None
    email = payload.get("email")
    return str(sub), str(email) if email else None


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


def _auth_configured() -> bool:
    settings = get_settings()
    return bool(
        settings.supabase_jwks_url or settings.supabase_jwt_secret or settings.clerk_secret_key
    )


async def resolve_user(request: Request) -> AuthUser | None:
    settings = get_settings()
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:].strip()
        if token:
            if settings.supabase_jwks_url or settings.supabase_jwt_secret:
                verified = _verify_supabase_bearer(token)
                if verified:
                    supabase_user_id, email = verified
                    return AuthUser(
                        id=uuid.uuid5(uuid.NAMESPACE_URL, supabase_user_id),
                        supabase_user_id=supabase_user_id,
                        email=email,
                    )
            if settings.clerk_secret_key:
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

    if settings.dev_auth_enabled and not _auth_configured():
        dev_id = request.headers.get("X-Dev-User-Id", "dev-user")
        return AuthUser(
            id=uuid.uuid5(uuid.NAMESPACE_DNS, dev_id),
            clerk_id=dev_id,
        )
    if settings.dev_auth_enabled and _auth_configured():
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
