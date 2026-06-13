from __future__ import annotations

import httpx
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    version: str | None = None


class TcgScanClient:
    def __init__(self, base_url: str = "http://localhost:8000") -> None:
        self._base_url = base_url.rstrip("/")

    async def health(self) -> HealthResponse:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{self._base_url}/v1/health", timeout=10.0)
            r.raise_for_status()
            return HealthResponse.model_validate(r.json())
