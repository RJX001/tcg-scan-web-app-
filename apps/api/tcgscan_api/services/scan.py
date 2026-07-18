"""Scan orchestrator: detect -> embed -> ANN -> ocr -> rerank -> top-K.

The Modal stages run in parallel where it's safe (embed + ocr both consume the
cropped image). Final ranking is `cos_sim * ocr_match * popularity_prior`.
"""

from __future__ import annotations

import asyncio
import hashlib
import time
import uuid
from dataclasses import dataclass
from typing import Literal

import structlog
from opentelemetry import metrics, trace
from pydantic import BaseModel, Field
from qdrant_client.http import models as qm

from tcgscan_api.db.session import get_sessionmaker
from tcgscan_api.services.cache import cache_get, cache_set
from tcgscan_api.services.grade_roi import GradeVerdict, compute_verdict
from tcgscan_api.services.image_crop import crop_image_b64
from tcgscan_api.services.ml_client import MLClient
from tcgscan_api.services.qdrant import search_similar
from tcgscan_api.services.slug import card_slug

log = structlog.get_logger()

tracer = trace.get_tracer("tcgscan_api.scan")
meter = metrics.get_meter("tcgscan_api.scan")

SCAN_DURATION = meter.create_histogram(
    "tcgscan.scan.duration",
    unit="s",
    description="End-to-end scan duration",
)
SCAN_STAGE_DURATION = meter.create_histogram(
    "tcgscan.scan.stage.duration",
    unit="s",
    description="Per-stage scan duration",
)
SCAN_COUNT = meter.create_counter(
    "tcgscan.scan.count",
    description="Scan requests by outcome",
)

ScanOutcome = Literal["ok", "error", "cache_hit"]
ScanStage = Literal["detect", "embed_ocr_grade", "ann_search", "rerank", "verdict"]


class DetectBBox(BaseModel):
    x: float = 0.0
    y: float = 0.0
    w: float = 1.0
    h: float = 1.0
    angle: float = 0.0


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
    popularity_boost: float = 1.0


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
    bbox: DetectBBox | None = None
    stages_ms: dict[str, float] | None = None


@dataclass
class ScanInput:
    image_b64: str
    game_hint: str | None = None
    top_k: int = 5


def _cache_key(image_b64: str) -> str:
    digest = hashlib.sha256(image_b64.encode("utf-8")).hexdigest()
    return f"scan:{digest}"


def _parse_bbox(detect_out: dict[str, object]) -> DetectBBox:
    bboxes = detect_out.get("bboxes")
    if isinstance(bboxes, list) and bboxes:
        first = bboxes[0]
        if isinstance(first, dict):
            return DetectBBox.model_validate(first)
    return DetectBBox()


def _ocr_match_score(
    *,
    name: str,
    number: str | None,
    set_code: str | None,
    ocr_text: str,
    ocr_fields: dict[str, object],
) -> float:
    score = 1.0
    ocr_lower = (ocr_text or "").lower()
    if ocr_lower and name.lower() in ocr_lower:
        score *= 1.25
    if number:
        num_part = str(number).split("/")[0].strip().lower()
        if num_part and num_part in ocr_lower:
            score *= 1.15
    if set_code and set_code.lower() in ocr_lower:
        score *= 1.1
    field_name = ocr_fields.get("name")
    if isinstance(field_name, str) and field_name.lower() in name.lower():
        score *= 1.2
    field_num = ocr_fields.get("number")
    if isinstance(field_num, str) and number and field_num in str(number):
        score *= 1.15
    return score


def _popularity_boost(payload: dict[str, object]) -> float:
    raw = payload.get("popularity")
    if raw is None:
        return 1.0
    if isinstance(raw, (int, float)):
        pop = float(raw)
    elif isinstance(raw, str):
        try:
            pop = float(raw)
        except ValueError:
            return 1.0
    else:
        return 1.0
    # Map popularity 0–1 to a small boost band [0.95, 1.05]
    return 0.95 + max(0.0, min(1.0, pop)) * 0.1


def _rerank(
    points: list[qm.ScoredPoint], ocr_text: str, ocr_fields: dict[str, object]
) -> list[ScanMatch]:
    matches: list[ScanMatch] = []
    for p in points:
        payload = p.payload or {}
        name = str(payload.get("name") or "")
        game = payload.get("game")
        set_code = payload.get("set_code")
        number = payload.get("number")
        slug = None
        if game and set_code:
            slug = card_slug(
                str(game), str(set_code) if set_code else None, str(number) if number else None
            )
        ocr_match = _ocr_match_score(
            name=name,
            number=str(number) if number else None,
            set_code=str(set_code) if set_code else None,
            ocr_text=ocr_text,
            ocr_fields=ocr_fields,
        )
        pop_boost = _popularity_boost(payload)
        cos = max(0.0, min(1.0, float(p.score)))
        matches.append(
            ScanMatch(
                card_id=str(payload.get("card_id") or p.id),
                slug=slug,
                name=name or None,
                game=str(game) if game else None,
                set_code=str(set_code) if set_code else None,
                number=str(number) if number else None,
                score=min(1.0, cos * ocr_match * pop_boost),
                cos_sim=cos,
                ocr_boost=ocr_match,
                popularity_boost=pop_boost,
            )
        )
    matches.sort(key=lambda m: m.score, reverse=True)
    return matches


async def _catalog_fallback_matches(*, game: str | None, top_k: int) -> list[ScanMatch]:
    """When Qdrant is empty, return seed catalog cards so local demo still works."""
    if not game:
        return []
    from tcgscan_api.repositories.cards import CardsRepo

    async with get_sessionmaker()() as session:
        cards = await CardsRepo(session).list_by_game(game, limit=top_k)
    out: list[ScanMatch] = []
    for i, card in enumerate(cards):
        game_val = card.game.value if hasattr(card.game, "value") else str(card.game)
        slug = card_slug(game_val, card.set_code, card.number)
        score = max(0.25, 0.5 - i * 0.05)
        out.append(
            ScanMatch(
                card_id=str(card.id),
                slug=slug,
                name=card.name,
                game=game_val,
                set_code=card.set_code,
                number=card.number,
                score=score,
                cos_sim=score,
                ocr_boost=1.0,
                popularity_boost=1.0,
            )
        )
    return out


def _record_scan_outcome(*, duration_s: float, outcome: ScanOutcome) -> None:
    attrs = {"tcgscan.scan.outcome": outcome}
    SCAN_DURATION.record(duration_s, attrs)
    SCAN_COUNT.add(1, attrs)


def _record_stage_duration(*, stage: ScanStage, duration_s: float) -> None:
    SCAN_STAGE_DURATION.record(duration_s, {"tcgscan.scan.stage": stage})


def _set_run_span_match_attrs(span: trace.Span, matches: list[ScanMatch]) -> None:
    span.set_attribute("tcgscan.scan.match_count", len(matches))
    if matches:
        span.set_attribute("tcgscan.scan.top_score", matches[0].score)


async def run_scan(payload: ScanInput) -> ScanResult:
    with tracer.start_as_current_span("scan.run") as run_span:
        run_span.set_attribute("tcgscan.scan.top_k", payload.top_k)
        if payload.game_hint is not None:
            run_span.set_attribute("tcgscan.scan.game_hint", payload.game_hint)

        t_total = time.perf_counter()
        outcome: ScanOutcome = "ok"

        try:
            key = _cache_key(payload.image_b64)
            cached = await cache_get(key)
            if cached is not None:
                try:
                    result = ScanResult.model_validate({**cached, "cached": True})
                    run_span.set_attribute("tcgscan.scan.cache_hit", True)
                    _set_run_span_match_attrs(run_span, result.matches)
                    outcome = "cache_hit"
                    return result
                except Exception:
                    pass

            run_span.set_attribute("tcgscan.scan.cache_hit", False)

            stages: dict[str, float] = {}
            ml = MLClient()
            try:
                with tracer.start_as_current_span("scan.detect"):
                    t0 = time.perf_counter()
                    detect_out = await ml.detect(payload.image_b64)
                    bbox = _parse_bbox(detect_out)
                    cropped_b64 = crop_image_b64(payload.image_b64, bbox.model_dump())
                    stage_s = time.perf_counter() - t0
                    stages["detect"] = stage_s * 1000
                    _record_stage_duration(stage="detect", duration_s=stage_s)

                with tracer.start_as_current_span("scan.embed_ocr_grade"):
                    t1 = time.perf_counter()
                    vector, ocr_out, grade_out = await asyncio.gather(
                        ml.embed(cropped_b64),
                        ml.ocr(cropped_b64),
                        ml.grade(cropped_b64),
                    )
                    stage_s = time.perf_counter() - t1
                    stages["embed_ocr_grade"] = stage_s * 1000
                    _record_stage_duration(stage="embed_ocr_grade", duration_s=stage_s)

                ocr_text = str(ocr_out.get("text") or "")
                ocr_fields = ocr_out.get("fields")
                if not isinstance(ocr_fields, dict):
                    ocr_fields = {}

                with tracer.start_as_current_span("scan.ann_search") as ann_span:
                    t2 = time.perf_counter()
                    try:
                        points = await search_similar(
                            vector=vector, game=payload.game_hint, top_k=20
                        )
                    except Exception as exc:
                        ann_span.record_exception(exc)
                        ann_span.set_attribute("tcgscan.scan.qdrant_unavailable", True)
                        log.warning("scan.qdrant_unavailable", error=str(exc))
                        points = []
                    stage_s = time.perf_counter() - t2
                    stages["ann_search"] = stage_s * 1000
                    _record_stage_duration(stage="ann_search", duration_s=stage_s)

                with tracer.start_as_current_span("scan.rerank") as rerank_span:
                    t3 = time.perf_counter()
                    matches = _rerank(points, ocr_text, ocr_fields)
                    catalog_fallback = False
                    if not matches and payload.game_hint:
                        matches = await _catalog_fallback_matches(
                            game=payload.game_hint, top_k=payload.top_k
                        )
                        catalog_fallback = True
                        log.info(
                            "scan.catalog_fallback", game=payload.game_hint, count=len(matches)
                        )
                    rerank_span.set_attribute("tcgscan.scan.catalog_fallback", catalog_fallback)
                    stage_s = time.perf_counter() - t3
                    _record_stage_duration(stage="rerank", duration_s=stage_s)

                condition = ConditionEstimate.model_validate(grade_out)

                if matches and condition.psa_high is not None:
                    with tracer.start_as_current_span("scan.verdict") as verdict_span:
                        t4 = time.perf_counter()
                        try:
                            card_uuid = uuid.UUID(matches[0].card_id)
                            async with get_sessionmaker()() as session:
                                verdict = await compute_verdict(
                                    session, card_uuid, psa_high=condition.psa_high
                                )
                                if verdict is not None:
                                    condition = condition.model_copy(update={"verdict": verdict})
                        except (ValueError, Exception) as exc:
                            verdict_span.record_exception(exc)
                            log.warning("scan.verdict_skipped", error=str(exc))
                        stage_s = time.perf_counter() - t4
                        _record_stage_duration(stage="verdict", duration_s=stage_s)

                result = ScanResult(
                    matches=matches[: payload.top_k],
                    condition=condition,
                    bbox=bbox,
                    stages_ms=stages,
                )
            finally:
                await ml.aclose()

            await cache_set(key, result.model_dump(mode="json"), ttl_s=86400)
            _set_run_span_match_attrs(run_span, result.matches)
            return result
        except Exception:
            outcome = "error"
            raise
        finally:
            _record_scan_outcome(duration_s=time.perf_counter() - t_total, outcome=outcome)
