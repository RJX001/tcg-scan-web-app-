from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ENV_FILE = _REPO_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), extra="ignore")

    environment: str = Field(default="development", alias="ENVIRONMENT")
    cors_origins: str = Field(default="http://localhost:3000", alias="CORS_ORIGINS")

    database_url: str = Field(
        default="postgresql+asyncpg://tcgscan:tcgscan@localhost:5432/tcgscan",
        alias="DATABASE_URL",
    )
    qdrant_url: str = Field(default="http://localhost:6333", alias="QDRANT_URL")
    qdrant_api_key: str | None = Field(default=None, alias="QDRANT_API_KEY")
    redis_url: str = Field(default="redis://localhost:6379", alias="REDIS_URL")

    modal_detect_url: str | None = Field(default=None, alias="MODAL_DETECT_URL")
    modal_embed_url: str | None = Field(default=None, alias="MODAL_EMBED_URL")
    modal_ocr_url: str | None = Field(default=None, alias="MODAL_OCR_URL")
    modal_grade_url: str | None = Field(default=None, alias="MODAL_GRADE_URL")

    embedding_dim: int = 1024
    qdrant_collection: str = "cards"
    scan_cache_ttl_s: int = 60 * 60 * 24

    ebay_app_id: str | None = Field(default=None, alias="EBAY_APP_ID")
    ebay_cert_id: str | None = Field(default=None, alias="EBAY_CERT_ID")
    ebay_marketplace_id: str = Field(default="EBAY_GB", alias="EBAY_MARKETPLACE_ID")
    tcg_api_key: str | None = Field(default=None, alias="TCG_API_KEY")
    apify_token: str | None = Field(default=None, alias="APIFY_TOKEN")

    clerk_secret_key: str | None = Field(default=None, alias="CLERK_SECRET_KEY")
    clerk_authorized_parties: str | None = Field(
        default="http://localhost:3000", alias="CLERK_AUTHORIZED_PARTIES"
    )
    owner_email: str = Field(default="", alias="OWNER_EMAIL")
    dev_auth_enabled: bool = Field(default=True, alias="DEV_AUTH_ENABLED")
    free_scans_per_day: int = Field(default=10, alias="FREE_SCANS_PER_DAY")
    free_portfolio_limit: int = Field(default=25, alias="FREE_PORTFOLIO_LIMIT")

    stripe_secret_key: str | None = Field(default=None, alias="STRIPE_SECRET_KEY")
    stripe_webhook_secret: str | None = Field(default=None, alias="STRIPE_WEBHOOK_SECRET")
    stripe_pro_price_id: str | None = Field(default=None, alias="STRIPE_PRO_PRICE_ID")
    stripe_success_url: str = Field(
        default="http://localhost:3000/account?checkout=success", alias="STRIPE_SUCCESS_URL"
    )
    stripe_cancel_url: str = Field(
        default="http://localhost:3000/account?checkout=cancel", alias="STRIPE_CANCEL_URL"
    )

    sentry_dsn_api: str | None = Field(default=None, alias="SENTRY_DSN_API")
    otel_exporter_otlp_endpoint: str | None = Field(
        default=None, alias="OTEL_EXPORTER_OTLP_ENDPOINT"
    )
    api_public_url: str = Field(default="http://localhost:8000", alias="API_PUBLIC_URL")

    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    langsmith_api_key: str | None = Field(default=None, alias="LANGSMITH_API_KEY")
    langsmith_project: str = Field(default="tcg-scan-dev", alias="LANGSMITH_PROJECT")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
