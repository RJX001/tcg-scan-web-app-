"""Scan orchestrator: detect -> embed -> ANN -> ocr -> rerank -> top-K.

The Modal stages run in parallel where it's safe (embed + ocr both consume the
cropped image). Final ranking is `cos_sim * ocr_match * popularity_prior`.
"""

from __future__ import annotations

import asyncio
import hashlib
import uuid
from dataclasses import dataclass

import structlog
from pydantic import BaseModel, Field
from qdrant_client.http import models as qm

from tcgscan_api.db.session import get_sessionmaker
from tcgscan_api.services.cache import cache_get, cache_set
from tcgscan_api.services.grade_roi import GradeVerdict, compute_verdict
from tcgscan_api.services.ml_client import MLClient
from tcgscan_api.services.qdrant import search_similar
from tcgscan_api.services.slug import card_slug

log = structlog.get_logger()


class ScanMatch(BaseModel):
    card_id: str
    slug: str | None = None
    name: str | None = None
    game: str | None = None
    set_code: str | None = None
    number: str | None = None
    score: float = Field(ge=0.0, le=1.0)
    cos_sim: float
    ocr_boost: float = 1.0


class ConditionEstimate(BaseModel):
    overall: float | None = None
    centering: float | None = None
    corners: float | None = None
    edges: float | None = None
    surface: float | None = None
    psa_low: int | None = None
    psa_high: int | None = None
    psa_label: str | None = None
    confidence: float | None = None
    model: str | None = None
    verdict: GradeVerdict | None = None


class ScanResult(BaseModel):
    matches: list[ScanMatch]
    condition: ConditionEstimate
    cached: bool = False


@dataclass
class ScanInput:
    image_b64: str
    game_hint: str | None = None
    top_k: int = 5


def _cache_key(image_b64: str) -> str:
    digest = hashlib.sha256(image_b64.encode("utf-8")).hexdigest()
    return f"scan:{digest}"


def _rerank(points: list[qm.ScoredPoint], ocr_text: str) -> list[ScanMatch]:
    matches: list[ScanMatch] = []
    ocr_lower = (ocr_text or "").lower()
    for p in points:
        payload = p.payload or {}
        name = payload.get("name") or ""
        game = payload.get("game")
        set_code = payload.get("set_code")
        number = payload.get("number")
        slug = None
        if game and set_code:
            slug = card_slug(str(game), str(set_code) if set_code else None, str(number) if number else None)
        ocr_match = 1.0
        if ocr_lower and isinstance(name, str) and name.lower() in ocr_lower:
            ocr_match = 1.25
        cos = max(0.0, min(1.0, float(p.score)))
        matches.append(
            ScanMatch(
                card_id=str(payload.get("card_id") or p.id),
                slug=slug,
                name=name or None,
                game=game,
                set_code=set_code,
                number=number,
                score=min(1.0, cos * ocr_match),
                cos_sim=cos,
                ocr_boost=ocr_match,
            )
        )
    matches.sort(key=lambda m: m.score, reverse=True)
    return matches


async def run_scan(payload: ScanInput) -> ScanResult:
    key = _cache_key(payload.image_b64)
    cached = await cache_get(key)
    if cached is not None:
        try:
            return ScanResult.model_validate({**cached, "cached": True})
        except Exception:
            pass

    ml = MLClient()
    try:
        # Stage 1: detect (sequential — provides crop info downstream stages assume).
        await ml.detect(payload.image_b64)
        # Stage 2+3: embed + ocr + grade in parallel.
        vector, ocr_out, grade_out = await asyncio.gather(
            ml.embed(payload.image_b64),
            ml.ocr(payload.image_b64),
            ml.grade(payload.image_b64),
        )

        try:
            points = await search_similar(vector=vector, game=payload.game_hint, top_k=20)
        except Exception as exc:
            log.warning("scan.qdrant_unavailable", error=str(exc))
            points = []

        matches = _rerank(points, ocr_out.get("text", ""))
        condition = ConditionEstimate.model_validate(grade_out)

        if matches and condition.psa_high is not None:
            try:
                card_uuid = uuid.UUID(matches[0].card_id)
                async with get_sessionmaker()() as session:
                    verdict = await compute_verdict(
                        session, card_uuid, psa_high=condition.psa_high
                    )
                    if verdict is not None:
                        condition = condition.model_copy(update={"verdict": verdict})
            except (ValueError, Exception) as exc:
                log.warning("scan.verdict_skipped", error=str(exc))

        result = ScanResult(
            matches=matches[: payload.top_k],
            condition=condition,
        )
    finally:
        await ml.aclose()

    await cache_set(key, result.model_dump(mode="json"), ttl_s=86400)
    return result
