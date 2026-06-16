"""Resilient admin sources status — never crash the /admin/sources page."""

from __future__ import annotations

from typing import Any

import structlog
from sqlalchemy.exc import DBAPIError, ProgrammingError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from tcgscan_api.repositories.admin import AdminRepo
from tcgscan_api.services.catalogue_import import catalogue_stats
from tcgscan_api.services.ebay_ingest import ebay_listing_stats
from tcgscan_api.services.source_audit import build_sources_status

log = structlog.get_logger()

_CATALOG_SOURCES = (
    ("pokemon", "pokemontcg"),
    ("scryfall", "scryfall"),
    ("ygopro", "ygoprodeck"),
    ("one_piece", "optcgapi"),
    ("dragon_ball_fusion_world", "bandai"),
    ("dragon_ball_masters", "bandai"),
)


def _fallback_catalog_stats() -> dict[str, Any]:
    return {
        "catalog_stats": [
            {
                "source_key": key,
                "catalog_source": source,
                "card_count": 0,
                "last_success_at": None,
                "last_run_id": None,
                "last_sample_at": None,
                "last_full_at": None,
                "current_run_status": None,
                "current_run_id": None,
            }
            for key, source in _CATALOG_SOURCES
        ]
    }


def _fallback_ebay_stats() -> dict[str, Any]:
    return {
        "pricing_stats": [
            {
                "source_key": "ebay",
                "listing_count": 0,
                "last_success_at": None,
                "last_run_id": None,
            }
        ]
    }


async def get_admin_sources_status(session: AsyncSession) -> dict[str, Any]:
    warnings: list[str] = []

    try:
        data_health = await AdminRepo(session).data_health()
    except SQLAlchemyError as exc:
        await session.rollback()
        log.warning("admin_sources.data_health_failed", error=str(exc))
        data_health = []
        warnings.append("data_health_unavailable")

    payload = build_sources_status(data_health)

    try:
        payload.update(await catalogue_stats(session))
    except (ProgrammingError, DBAPIError, SQLAlchemyError) as exc:
        await session.rollback()
        log.warning("admin_sources.catalog_stats_failed", error=str(exc))
        payload.update(_fallback_catalog_stats())
        warnings.append("catalog_stats_degraded")
    except Exception as exc:
        log.warning("admin_sources.catalog_stats_failed", error=str(exc))
        payload.update(_fallback_catalog_stats())
        warnings.append("catalog_stats_degraded")

    try:
        payload.update(await ebay_listing_stats(session))
    except (ProgrammingError, DBAPIError, SQLAlchemyError) as exc:
        await session.rollback()
        log.warning("admin_sources.ebay_stats_failed", error=str(exc))
        payload.update(_fallback_ebay_stats())
        warnings.append("ebay_stats_unavailable")
    except Exception as exc:
        log.warning("admin_sources.ebay_stats_failed", error=str(exc))
        payload.update(_fallback_ebay_stats())
        warnings.append("ebay_stats_unavailable")

    if warnings:
        payload["status_warnings"] = warnings

    return payload
