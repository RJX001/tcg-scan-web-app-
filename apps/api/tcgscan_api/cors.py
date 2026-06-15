"""CORS origin parsing and middleware defaults."""

from __future__ import annotations

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from tcgscan_api.config import get_settings

CORS_ALLOW_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]


def parse_cors_origins(raw: str) -> list[str]:
    """Parse comma-separated origin URLs into a deduplicated list."""
    seen: set[str] = set()
    origins: list[str] = []
    for part in raw.split(","):
        origin = part.strip()
        if not origin or origin in seen:
            continue
        seen.add(origin)
        origins.append(origin)
    return origins


def cors_origins_from_settings() -> list[str]:
    return parse_cors_origins(get_settings().cors_origins)


def wrap_with_cors(fastapi_app: FastAPI, origins: list[str] | None = None) -> CORSMiddleware:
    """Wrap the FastAPI app so all responses, including 401/403/500, get CORS headers."""
    return CORSMiddleware(
        fastapi_app,
        allow_origins=origins or cors_origins_from_settings(),
        allow_credentials=True,
        allow_methods=CORS_ALLOW_METHODS,
        allow_headers=["*"],
    )
