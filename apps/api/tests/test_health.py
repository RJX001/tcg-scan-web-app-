import pytest
from httpx import ASGITransport, AsyncClient

from tcgscan_api.main import app


@pytest.mark.asyncio
async def test_health() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
