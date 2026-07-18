"""Log severity coverage for ingest/import job failure paths."""

from __future__ import annotations

import pytest
import respx
import structlog
from httpx import Response
from structlog.testing import capture_logs

from tcgscan_api.config import get_settings
from tcgscan_api.services import catalogue_import as catalogue_import_mod
from tcgscan_api.services import catalogue_ingest as catalogue_ingest_mod
from tcgscan_api.services import ebay_ingest as ebay_ingest_mod
from tcgscan_api.services.catalogue_import import start_full_catalogue_import
from tcgscan_api.services.catalogue_ingest import run_catalogue_ingest
from tcgscan_api.services.ebay_ingest import run_ebay_ingest

OAUTH_RESPONSE = {"access_token": "test-token", "expires_in": 7200}


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.asyncio
@respx.mock
async def test_catalogue_import_failed_logs_error(sqlite_session: object) -> None:
    respx.get("https://api.scryfall.com/cards/search").mock(
        return_value=Response(500, json={"error": "fail"})
    )

    with capture_logs() as logs:
        catalogue_import_mod.log = structlog.get_logger()
        result = await start_full_catalogue_import(
            sqlite_session, "scryfall", dry_run=False, force=True
        )

    assert result.status == "failed"
    failed_logs = [entry for entry in logs if entry.get("event") == "catalogue_import.failed"]
    assert len(failed_logs) == 1
    assert failed_logs[0]["log_level"] == "error"
    assert failed_logs[0]["source"] == "scryfall"
    assert "error" in failed_logs[0]


@pytest.mark.asyncio
@respx.mock
async def test_catalogue_ingest_failed_logs_error(sqlite_session: object) -> None:
    respx.get("https://optcgapi.com/api/allSetCards/").mock(
        return_value=Response(500, json={"detail": "upstream error"})
    )

    with capture_logs() as logs:
        catalogue_ingest_mod.log = structlog.get_logger()
        result = await run_catalogue_ingest(sqlite_session, "one_piece", limit=10, dry_run=False)

    assert result.status == "failed"
    failed_logs = [entry for entry in logs if entry.get("event") == "catalogue_ingest.failed"]
    assert len(failed_logs) == 1
    assert failed_logs[0]["log_level"] == "error"
    assert failed_logs[0]["source"] == "one_piece"
    assert "error" in failed_logs[0]


@pytest.mark.asyncio
@respx.mock
async def test_ebay_ingest_failed_logs_error(
    sqlite_session: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EBAY_APP_ID", "app")
    monkeypatch.setenv("EBAY_CERT_ID", "cert")
    get_settings.cache_clear()
    respx.post("https://api.ebay.com/identity/v1/oauth2/token").mock(
        return_value=Response(200, json=OAUTH_RESPONSE)
    )
    respx.get("https://api.ebay.com/buy/browse/v1/item_summary/search").mock(
        return_value=Response(500, json={"errors": [{"message": "fail"}]})
    )

    with capture_logs() as logs:
        ebay_ingest_mod.log = structlog.get_logger()
        result = await run_ebay_ingest(sqlite_session, dry_run=False)

    assert result.status == "failed"
    failed_logs = [entry for entry in logs if entry.get("event") == "ebay_ingest.failed"]
    assert len(failed_logs) == 1
    assert failed_logs[0]["log_level"] == "error"
    assert "error" in failed_logs[0]
