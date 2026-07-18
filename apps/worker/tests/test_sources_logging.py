"""Log severity coverage for worker sources (W4 package)."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
import structlog
from structlog.testing import capture_logs

from tcgscan_api.db.models import Game
from tcgscan_worker import embedding as embedding_mod
from tcgscan_worker.sources import ebay_auth as ebay_auth_mod
from tcgscan_worker.sources.psa_pop import PsaPopSource


def _events(cap: list[dict[str, object]], event: str, *, level: str) -> list[dict[str, object]]:
    return [
        entry for entry in cap if entry.get("event") == event and entry.get("log_level") == level
    ]


@pytest.mark.asyncio
async def test_embed_run_degraded_when_download_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    card_id = uuid.uuid4()
    card = SimpleNamespace(
        id=card_id,
        game=Game.pokemon,
        name="Pikachu",
        set_code="base1",
        number="58/102",
        image_urls={"large": "https://images.example/card.png"},
    )

    @asynccontextmanager
    async def _session():
        class _Result:
            def scalars(self) -> SimpleNamespace:
                return SimpleNamespace(all=lambda: [card])

        class _Session:
            async def execute(self, _stmt: object) -> _Result:
                return _Result()

        yield _Session()

    mock_qclient = AsyncMock()
    mock_qclient.get_collections.return_value = SimpleNamespace(collections=[])
    mock_qclient.create_collection = AsyncMock()
    mock_qclient.upsert = AsyncMock()
    mock_qclient.close = AsyncMock()

    monkeypatch.setattr(embedding_mod, "get_sessionmaker", lambda: lambda: _session())
    monkeypatch.setattr(embedding_mod, "AsyncQdrantClient", lambda **_kwargs: mock_qclient)
    monkeypatch.delenv("MODAL_EMBED_URL", raising=False)

    async def _fail_download(_url: str, *, card_id: str) -> tuple[None, bool]:
        return None, True

    embedding_mod.log = structlog.get_logger()
    monkeypatch.setattr(embedding_mod, "_download_image_b64", _fail_download)

    with capture_logs() as cap:
        total = await embedding_mod.embed_game("pokemon", limit=1)

    assert total == 1

    done = _events(cap, "embed.run.done", level="info")
    assert len(done) == 1
    assert done[0]["embedded"] == 0
    assert done[0]["stubbed"] == 1
    assert done[0]["download_failed"] == 1
    assert done[0]["skipped_no_image"] == 0
    assert done[0]["total"] == 1

    degraded = _events(cap, "embed.run.degraded", level="error")
    assert len(degraded) == 1
    assert degraded[0]["stubbed"] == 1
    assert degraded[0]["total"] == 1


@pytest.mark.asyncio
async def test_embed_skipped_no_image_in_counters(monkeypatch: pytest.MonkeyPatch) -> None:
    card = SimpleNamespace(
        id=uuid.uuid4(),
        game=Game.pokemon,
        name="No Image",
        set_code="base1",
        number="1/102",
        image_urls={},
    )

    @asynccontextmanager
    async def _session():
        class _Result:
            def scalars(self) -> SimpleNamespace:
                return SimpleNamespace(all=lambda: [card])

        class _Session:
            async def execute(self, _stmt: object) -> _Result:
                return _Result()

        yield _Session()

    mock_qclient = AsyncMock()
    mock_qclient.get_collections.return_value = SimpleNamespace(
        collections=[SimpleNamespace(name="cards")]
    )
    mock_qclient.close = AsyncMock()

    monkeypatch.setattr(embedding_mod, "get_sessionmaker", lambda: lambda: _session())
    monkeypatch.setattr(embedding_mod, "AsyncQdrantClient", lambda **_kwargs: mock_qclient)
    embedding_mod.log = structlog.get_logger()

    with capture_logs() as cap:
        total = await embedding_mod.embed_game("pokemon", limit=1)

    assert total == 0
    done = _events(cap, "embed.run.done", level="info")
    assert done[0]["skipped_no_image"] == 1
    assert done[0]["stubbed"] == 0
    assert len(_events(cap, "embed.run.degraded", level="error")) == 0


@pytest.mark.asyncio
async def test_ebay_auth_missing_credentials_logs_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EBAY_OAUTH_TOKEN", raising=False)
    monkeypatch.delenv("EBAY_APP_ID", raising=False)
    monkeypatch.delenv("EBAY_CERT_ID", raising=False)
    ebay_auth_mod._cached_token = None
    ebay_auth_mod._cached_expires = None
    ebay_auth_mod.log = structlog.get_logger()

    with capture_logs() as cap:
        with pytest.raises(ValueError, match="EBAY_OAUTH_TOKEN"):
            await ebay_auth_mod.get_ebay_oauth_token()

    errors = _events(cap, "ebay.auth_failed", level="error")
    assert len(errors) == 1
    assert errors[0]["reason"] == "missing_credentials"


@pytest.mark.asyncio
async def test_psa_pop_per_spec_logs_debug() -> None:
    mock_client = MagicMock()
    mock_client.get_json = AsyncMock(
        return_value={"PSASpecPopulationModel": [{"Grade1": 10, "Grade2": 5}]}
    )
    source = PsaPopSource(client=mock_client)

    with capture_logs() as cap:
        records = await source.population_for_spec(12345)

    assert len(records) == 2
    fetched = _events(cap, "psa_pop.fetched", level="debug")
    assert len(fetched) == 1
    assert fetched[0]["spec_id"] == 12345
    assert fetched[0]["grades"] == 2
    assert len(_events(cap, "psa_pop.fetched", level="info")) == 0
