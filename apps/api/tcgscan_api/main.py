from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from tcgscan_api.config import get_settings
from tcgscan_api.cors import cors_origins_from_settings, wrap_with_cors
from tcgscan_api.errors import AppError
from tcgscan_api.middleware.auth import AuthMiddleware
from tcgscan_api.routes import (
    admin,
    billing,
    cards,
    ebay,
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


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    init_observability()
    settings = get_settings()
    cors_origins = cors_origins_from_settings()
    log.info("Allowed CORS origins: %s", cors_origins)
    if settings.environment == "production" and not (
        settings.supabase_jwt_secret or settings.supabase_jwks_url
    ):
        log.critical(
            "api.startup.supabase_missing",
            msg="SUPABASE_JWT_SECRET or SUPABASE_JWKS_URL is required when ENVIRONMENT=production",
        )
    yield


fastapi_app = FastAPI(title="TCG Chart API", version="0.0.0", lifespan=lifespan)
fastapi_app.add_middleware(AuthMiddleware)


@fastapi_app.exception_handler(AppError)
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


@fastapi_app.exception_handler(HTTPException)
async def http_exception_handler(_req: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@fastapi_app.exception_handler(Exception)
async def unhandled_exception_handler(_req: Request, exc: Exception) -> JSONResponse:
    log.exception("api.unhandled_exception", path=_req.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


fastapi_app.include_router(health.router, prefix="/v1")
fastapi_app.include_router(ebay.router, prefix="/v1")
fastapi_app.include_router(cards.router, prefix="/v1")
fastapi_app.include_router(scan.router, prefix="/v1")
fastapi_app.include_router(portfolio.router, prefix="/v1")
fastapi_app.include_router(billing.router, prefix="/v1")
fastapi_app.include_router(insights.router, prefix="/v1")
fastapi_app.include_router(market.router, prefix="/v1")
fastapi_app.include_router(searches.router, prefix="/v1")
fastapi_app.include_router(watchlist.router, prefix="/v1")
fastapi_app.include_router(admin.router, prefix="/v1")

# Outermost ASGI wrapper — uvicorn imports `app`.
app = wrap_with_cors(fastapi_app)
