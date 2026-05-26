from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

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
    tcg_api_key: str | None = Field(default=None, alias="TCG_API_KEY")
    apify_token: str | None = Field(default=None, alias="APIFY_TOKEN")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
