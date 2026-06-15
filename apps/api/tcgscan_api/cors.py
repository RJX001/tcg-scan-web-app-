"""CORS origin parsing and middleware defaults."""

from __future__ import annotations

CORS_ALLOW_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]

CORS_ALLOW_HEADERS = [
    "Authorization",
    "Content-Type",
    "Accept",
    "Origin",
    "X-Requested-With",
]


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
