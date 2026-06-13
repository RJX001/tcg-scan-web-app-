"""Embedding pipeline.

Walks `card_identity`, fetches each card's primary image, calls the Modal `embed`
endpoint (or a deterministic local stub when MODAL_EMBED_URL is unset), and
upserts the resulting 1024-dim vector into the Qdrant `cards` collection with
payload `{ card_id, game, name, set_code }` for filtered ANN search.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import os
from collections.abc import Iterable
from typing import Any

import httpx
import structlog
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qm
from sqlalchemy import select

from tcgscan_api.config import get_settings
from tcgscan_api.db.models import CardIdentity, Game
from tcgscan_api.db.session import get_sessionmaker
from tcgscan_worker.http import ResilientClient

log = structlog.get_logger()


def _stub_vector(seed: str, dim: int) -> list[float]:
    """Deterministic pseudo-embedding for local dev when no Modal endpoint is set."""
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    # Tile the 32-byte digest across `dim` floats in [-1, 1], L2-ish.
    vec = [((digest[i % 32] / 255.0) * 2.0 - 1.0) for i in range(dim)]
    norm = sum(v * v for v in vec) ** 0.5 or 1.0
    return [v / norm for v in vec]


async def _download_image_b64(image_url: str) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(image_url)
            resp.raise_for_status()
            return base64.b64encode(resp.content).decode("ascii")
    except (httpx.HTTPError, ValueError) as exc:
        log.warning("embed.download_failed", url=image_url, error=str(exc))
        return None


async def _embed_image(client: ResilientClient | None, *, image_url: str, dim: int) -> list[float]:
    image_b64 = await _download_image_b64(image_url)
    if client is None or not os.getenv("MODAL_EMBED_URL"):
        if image_b64:
            return _stub_vector(image_b64, dim)
        return _stub_vector(image_url, dim)
    if not image_b64:
        return _stub_vector(image_url, dim)
    payload: dict[str, Any] = await client.post_json("", json={"image_b64": image_b64})
    vec = payload.get("vector")
    if not isinstance(vec, list) or len(vec) != dim:
        log.warning("embed.bad_response", got_dim=len(vec) if isinstance(vec, list) else None)
        return _stub_vector(image_url, dim)
    return [float(x) for x in vec]


async def _ensure_collection(qclient: AsyncQdrantClient, collection: str, dim: int) -> None:
    existing = {c.name for c in (await qclient.get_collections()).collections}
    if collection in existing:
        return
    await qclient.create_collection(
        collection_name=collection,
        vectors_config=qm.VectorParams(size=dim, distance=qm.Distance.COSINE),
    )


def _card_uuid(card_id: object) -> str:
    return str(card_id)


async def embed_game(game: str, *, limit: int | None = None, batch: int = 64) -> int:
    settings = get_settings()
    qclient = AsyncQdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
    await _ensure_collection(qclient, settings.qdrant_collection, settings.embedding_dim)

    modal_url = os.getenv("MODAL_EMBED_URL")
    http_client = (
        ResilientClient(base_url=modal_url, rate_per_sec=5.0, burst=10) if modal_url else None
    )

    total = 0
    try:
        async with get_sessionmaker()() as session:
            stmt = select(CardIdentity)
            if game == "sports":
                stmt = stmt.where(
                    CardIdentity.game.in_(
                        [
                            Game.sports_baseball,
                            Game.sports_basketball,
                            Game.sports_football,
                            Game.sports_soccer,
                        ]
                    )
                )
            else:
                stmt = stmt.where(CardIdentity.game == Game(game))
            if limit is not None:
                stmt = stmt.limit(limit)
            cards: Iterable[CardIdentity] = (await session.execute(stmt)).scalars().all()

            buffer: list[qm.PointStruct] = []
            for card in cards:
                images: dict[str, Any] = dict(card.image_urls or {})
                image_url = str(
                    images.get("large")
                    or images.get("normal")
                    or images.get("front")
                    or images.get("hires")
                    or images.get("small")
                    or ""
                )
                if not image_url:
                    continue
                vec = await _embed_image(
                    http_client, image_url=image_url, dim=settings.embedding_dim
                )
                pop_seed = hashlib.sha256(str(card.id).encode()).digest()[0] / 255.0
                buffer.append(
                    qm.PointStruct(
                        id=_card_uuid(card.id),
                        vector=vec,
                        payload={
                            "card_id": str(card.id),
                            "game": str(
                                card.game.value if hasattr(card.game, "value") else card.game
                            ),
                            "name": card.name,
                            "set_code": card.set_code,
                            "number": card.number,
                            "popularity": pop_seed,
                        },
                    )
                )
                if len(buffer) >= batch:
                    await qclient.upsert(collection_name=settings.qdrant_collection, points=buffer)
                    total += len(buffer)
                    buffer.clear()
            if buffer:
                await qclient.upsert(collection_name=settings.qdrant_collection, points=buffer)
                total += len(buffer)
    finally:
        if http_client:
            await http_client.aclose()
        await qclient.close()
    log.info("embed.done", game=game, total=total)
    return total


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser("embed:catalog")
    parser.add_argument("--game", required=True)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args(argv)
    n = asyncio.run(embed_game(args.game, limit=args.limit))
    print(f"embedded={n} game={args.game}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
