from __future__ import annotations

from functools import lru_cache

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qm

from tcgscan_api.config import get_settings


@lru_cache(maxsize=1)
def get_qdrant() -> AsyncQdrantClient:
    settings = get_settings()
    return AsyncQdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)


async def search_similar(
    *, vector: list[float], game: str | None = None, top_k: int = 20
) -> list[qm.ScoredPoint]:
    settings = get_settings()
    flt = None
    if game:
        flt = qm.Filter(must=[qm.FieldCondition(key="game", match=qm.MatchValue(value=game))])
    result = await get_qdrant().query_points(
        collection_name=settings.qdrant_collection,
        query=vector,
        query_filter=flt,
        limit=top_k,
    )
    return list(result.points)
