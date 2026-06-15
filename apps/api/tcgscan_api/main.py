from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from tcgscan_api.config import get_settings
from tcgscan_api.cors import CORS_ALLOW_HEADERS, CORS_ALLOW_METHODS, parse_cors_origins
from tcgscan_api.errors import AppError
from tcgscan_api.middleware.auth import AuthMiddleware
from tcgscan_api.routes import (
    admin,
    billing,
    cards,
    health,
    insights,
    market,
    portfolio,
    scan,
    searches,
    watchlist,
)
from tcgscan_api.telemetry import init_observability


log = structlog.get_logger()


def _cors_origins_from_settings() -> list[str]:
    settings = get_settings()
    return parse_cors_origins(settings.cors_origins)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    init_observability()
    settings = get_settings()
    cors_origins = _cors_origins_from_settings()
    log.info("Allowed CORS origins: %s", cors_origins)
    if settings.environment == "production" and not (
        settings.supabase_jwt_secret or settings.supabase_jwks_url
    ):
        log.critical(
            "api.startup.supabase_missing",
            msg="SUPABASE_JWT_SECRET or SUPABASE_JWKS_URL is required when ENVIRONMENT=production",
        )
    yield


app = FastAPI(title="TCG Chart API", version="0.0.0", lifespan=lifespan)

# CORSMiddleware must be registered before auth so preflight/401 responses include CORS headers.
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins_from_settings(),
    allow_credentials=True,
    allow_methods=CORS_ALLOW_METHODS,
    allow_headers=CORS_ALLOW_HEADERS,
)
app.add_middleware(AuthMiddleware)


@app.exception_handler(AppError)
async def app_error_handler(_req: Request, exc: AppError) -> JSONResponse:
    """RFC 9457 problem-json mapping."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "type": f"about:blank#{exc.__class__.__name__}",
            "title": exc.__class__.__name__,
            "status": exc.status_code,
            "detail": exc.message,
        },
        media_type="application/problem+json",
    )


app.include_router(health.router, prefix="/v1")
app.include_router(cards.router, prefix="/v1")
app.include_router(scan.router, prefix="/v1")
app.include_router(portfolio.router, prefix="/v1")
app.include_router(billing.router, prefix="/v1")
app.include_router(insights.router, prefix="/v1")
app.include_router(market.router, prefix="/v1")
app.include_router(searches.router, prefix="/v1")
app.include_router(watchlist.router, prefix="/v1")
app.include_router(admin.router, prefix="/v1")
