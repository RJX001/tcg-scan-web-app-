"""Log severity coverage for SourceHttpClient retry / exhaustion."""

from __future__ import annotations

import httpx
import pytest
import respx
import structlog
from httpx import Response
from structlog.testing import capture_logs
from tenacity import wait_none

from tcgscan_api.sources import http_client as http_client_mod
from tcgscan_api.sources.http_client import SourceHttpClient, _GET_JSON_MAX_ATTEMPTS


@pytest.fixture(autouse=True)
def _no_retry_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(http_client_mod, "wait_exponential_jitter", lambda **_: wait_none())


@pytest.mark.asyncio
@respx.mock
async def test_retry_warnings_then_success_no_exhaustion_error() -> None:
    base = "https://source.test"
    path = "/cards"
    url = f"{base}{path}"
    respx.get(url).mock(
        side_effect=[
            Response(500),
            Response(503),
            Response(200, json={"ok": True}),
        ]
    )

    with capture_logs() as logs:
        http_client_mod.log = structlog.get_logger()
        client = SourceHttpClient(base_url=base, rate_per_sec=100.0, burst=10)
        try:
            payload = await client.get_json(path)
        finally:
            await client.aclose()

    assert payload == {"ok": True}
    retries = [e for e in logs if e.get("event") == "source_http.retry"]
    exhausted = [e for e in logs if e.get("event") == "source_http.exhausted"]
    assert len(retries) == 2
    assert all(e["log_level"] == "warning" for e in retries)
    assert [e["attempt"] for e in retries] == [1, 2]
    assert all(e["max_attempts"] == _GET_JSON_MAX_ATTEMPTS for e in retries)
    assert all(e["url"] == url for e in retries)
    assert all("error" in e for e in retries)
    assert exhausted == []


@pytest.mark.asyncio
@respx.mock
async def test_exhaustion_logs_warnings_then_error_and_raises() -> None:
    base = "https://source.test"
    path = "/cards"
    url = f"{base}{path}"
    respx.get(url).mock(return_value=Response(500))

    with capture_logs() as logs:
        http_client_mod.log = structlog.get_logger()
        client = SourceHttpClient(base_url=base, rate_per_sec=100.0, burst=10)
        try:
            with pytest.raises(httpx.HTTPStatusError):
                await client.get_json(path)
        finally:
            await client.aclose()

    retries = [e for e in logs if e.get("event") == "source_http.retry"]
    exhausted = [e for e in logs if e.get("event") == "source_http.exhausted"]
    assert len(retries) == _GET_JSON_MAX_ATTEMPTS - 1
    assert all(e["log_level"] == "warning" for e in retries)
    assert [e["attempt"] for e in retries] == list(range(1, _GET_JSON_MAX_ATTEMPTS))
    assert all(e["max_attempts"] == _GET_JSON_MAX_ATTEMPTS for e in retries)
    assert len(exhausted) == 1
    assert exhausted[0]["log_level"] == "error"
    assert exhausted[0]["url"] == url
    assert exhausted[0]["attempts"] == _GET_JSON_MAX_ATTEMPTS
    assert "error" in exhausted[0]


@pytest.mark.asyncio
@respx.mock
async def test_first_attempt_success_emits_no_retry_logs() -> None:
    base = "https://source.test"
    path = "/cards"
    url = f"{base}{path}"
    respx.get(url).mock(return_value=Response(200, json={"ok": True}))

    with capture_logs() as logs:
        http_client_mod.log = structlog.get_logger()
        client = SourceHttpClient(base_url=base, rate_per_sec=100.0, burst=10)
        try:
            await client.get_json(path)
        finally:
            await client.aclose()

    assert not any(e.get("event") == "source_http.retry" for e in logs)
    assert not any(e.get("event") == "source_http.exhausted" for e in logs)


@pytest.mark.asyncio
@respx.mock
async def test_non_retryable_status_emits_no_retry_or_exhaustion_logs() -> None:
    base = "https://source.test"
    path = "/cards"
    url = f"{base}{path}"
    respx.get(url).mock(return_value=Response(404))

    with capture_logs() as logs:
        http_client_mod.log = structlog.get_logger()
        client = SourceHttpClient(base_url=base, rate_per_sec=100.0, burst=10)
        try:
            with pytest.raises(httpx.HTTPStatusError):
                await client.get_json(path)
        finally:
            await client.aclose()

    assert not any(e.get("event") == "source_http.retry" for e in logs)
    assert not any(e.get("event") == "source_http.exhausted" for e in logs)
