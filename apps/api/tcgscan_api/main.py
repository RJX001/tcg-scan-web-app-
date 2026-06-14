from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from tcgscan_api.config import get_settings
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


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    init_observability()
    settings = get_settings()
    if settings.environment == "production" and not settings.clerk_secret_key:
        log.critical(
            "api.startup.clerk_missing",
            msg="CLERK_SECRET_KEY is required when ENVIRONMENT=production",
        )
    yield


_settings = get_settings()
_cors_origins = [o.strip() for o in _settings.cors_origins.split(",") if o.strip()]

app = FastAPI(title="TCG Chart API", version="0.0.0", lifespan=lifespan)
app.add_middleware(AuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
