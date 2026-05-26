from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from tcgscan_api.errors import AppError
from tcgscan_api.routes import cards, health, scan

app = FastAPI(title="TCG Scan API", version="0.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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
