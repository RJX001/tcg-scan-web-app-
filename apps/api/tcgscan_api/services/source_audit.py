"""Admin diagnostics for external data source configuration (never returns secret values)."""

from __future__ import annotations

import os
from typing import Any

import httpx
import structlog

from tcgscan_api.sources.dragon_ball_fusion_world import DragonBallFusionWorldClient
from tcgscan_api.sources.dragon_ball_masters import DragonBallMastersClient
from tcgscan_api.sources.one_piece import OnePieceClient
from tcgscan_api.sources.ygoprodeck import YgoProDeckClient

log = structlog.get_logger()


def _env_set(name: str) -> bool:
    return bool(os.getenv(name, "").strip())


def _env_flags(names: list[str]) -> dict[str, bool]:
    return {name: _env_set(name) for name in names}


def _ebay_configured() -> bool:
    return _env_set("EBAY_OAUTH_TOKEN") or (
        _env_set("EBAY_APP_ID") and _env_set("EBAY_CERT_ID")
    )


def _apify_cardmarket_enabled() -> bool:
    return _env_set("APIFY_TOKEN")


def _cardmarket_official_configured() -> bool:
    return _env_set("CARDMARKET_ACCESS_TOKEN") and _env_set("CARDMARKET_ACCESS_TOKEN_SECRET")


def _reddit_configured() -> bool:
    return (
        _env_set("REDDIT_CLIENT_ID")
        and _env_set("REDDIT_CLIENT_SECRET")
        and _env_set("REDDIT_USER_AGENT")
    )


def _catalog_game_status(
    game: str,
    *,
    api_module: str | None = None,
    optional_env: list[str] | None = None,
    worker_module: str | None = None,
    implementation: str = "working",
    notes: str = "",
) -> dict[str, Any]:
    worker_modules: dict[str, str] = {
        "pokemon": "apps/worker/tcgscan_worker/catalog/pokemon.py",
        "mtg": "apps/worker/tcgscan_worker/catalog/mtg.py",
        "yugioh": "apps/worker/tcgscan_worker/catalog/yugioh.py",
        "one_piece": "apps/worker/tcgscan_worker/catalog/one_piece.py",
        "dragon_ball_fusion_world": "apps/worker/tcgscan_worker/catalog/",
        "dragon_ball_masters": "apps/worker/tcgscan_worker/catalog/",
    }
    optional = optional_env or []
    configured = all(_env_set(name) for name in optional) if optional else True
    return {
        "id": game,
        "type": "catalog",
        "implementation": implementation,
        "configured": configured,
        "optional_env": _env_flags(optional),
        "api_module": api_module,
        "worker_module": worker_module or worker_modules.get(game),
        "ingest_command": f"pnpm ingest:catalog -- --game {game}" if game in worker_modules else None,
        "schedule": f"catalog-weekly-{game} (Temporal)" if game in worker_modules else None,
        "notes": notes,
    }


def build_sources_status(data_health: list[dict[str, object]] | None = None) -> dict[str, Any]:
    health_by_source = {str(row.get("source")): row for row in (data_health or [])}

    def _pricing(
        source_id: str,
        *,
        implementation: str,
        configured: bool,
        env_vars: list[str],
        worker_module: str,
        ingest_job: str,
        ingest_command: str,
        notes: str = "",
    ) -> dict[str, Any]:
        return {
            "id": source_id,
            "type": "pricing",
            "implementation": implementation,
            "configured": configured,
            "env": _env_flags(env_vars),
            "worker_module": worker_module,
            "ingest_job": ingest_job,
            "ingest_command": ingest_command,
            "data_health": health_by_source.get(source_id.replace("_sold", "").replace("_active", "ebay")),
            "notes": notes,
        }

    sources: list[dict[str, Any]] = [
        {
            "id": "ebay",
            "type": "pricing",
            "implementation": "pending_approval",
            "configured": _ebay_configured(),
            "env": _env_flags(
                [
                    "EBAY_OAUTH_TOKEN",
                    "EBAY_APP_ID",
                    "EBAY_CERT_ID",
                    "EBAY_INSIGHTS_TOKEN",
                    "EBAY_MARKETPLACE_ID",
                    "EBAY_AFFILIATE_TRACKING_ID",
                    "EBAY_AFFILIATE_CAMPAIGN_ID",
                ]
            ),
            "worker_modules": [
                "apps/worker/tcgscan_worker/sources/ebay_auth.py",
                "apps/worker/tcgscan_worker/sources/ebay_active.py",
                "apps/worker/tcgscan_worker/sources/ebay_sold.py",
            ],
            "ingest_jobs": ["EbayActiveWorkflow (15m)", "EbaySoldWorkflow (hourly)"],
            "ingest_command": "pnpm ingest:pricing -- --source ebay_active|ebay_sold",
            "data_health": health_by_source.get("ebay"),
            "notes": (
                "Official Browse API coded in worker; production ingest pending approval. "
                "EPN affiliate tagging not implemented."
            ),
        },
        _pricing(
            "tcgplayer",
            implementation="working",
            configured=_env_set("TCG_API_KEY"),
            env_vars=["TCG_API_KEY"],
            worker_module="apps/worker/tcgscan_worker/sources/tcgplayer.py",
            ingest_job="MarketplacePricingWorkflow (daily)",
            ingest_command="pnpm ingest:pricing -- --source tcgplayer",
        ),
        {
            "id": "cardmarket",
            "type": "pricing",
            "implementation": "partial",
            "configured": _apify_cardmarket_enabled(),
            "env": _env_flags(
                [
                    "APIFY_TOKEN",
                    "APIFY_CARDMARKET_DATASET_ID",
                    "APIFY_CARDMARKET_ACTOR_ID",
                    "CARDMARKET_APP_TOKEN",
                    "CARDMARKET_APP_SECRET",
                    "CARDMARKET_ACCESS_TOKEN",
                    "CARDMARKET_ACCESS_TOKEN_SECRET",
                ]
            ),
            "worker_module": "apps/worker/tcgscan_worker/sources/cardmarket.py",
            "ingest_job": "MarketplacePricingWorkflow (daily)",
            "ingest_command": "pnpm ingest:pricing -- --source cardmarket",
            "data_health": health_by_source.get("cardmarket"),
            "notes": "Apify dataset poll only. Pricing comes later from eBay/Cardmarket/paid sources.",
        },
        {
            "id": "reddit",
            "type": "trends",
            "implementation": "missing",
            "configured": _reddit_configured(),
            "env": _env_flags(["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USER_AGENT"]),
            "worker_module": None,
            "ingest_job": None,
            "ingest_command": None,
            "notes": "Not implemented. Hype/sentiment only — not card metadata or prices.",
        },
    ]

    catalog = [
        _catalog_game_status(
            "pokemon",
            api_module="apps/worker/tcgscan_worker/catalog/pokemon.py",
            optional_env=["POKEMONTCG_API_KEY"],
        ),
        _catalog_game_status(
            "mtg",
            api_module="apps/worker/tcgscan_worker/catalog/mtg.py",
        ),
        _catalog_game_status(
            "yugioh",
            api_module="apps/api/tcgscan_api/sources/ygoprodeck.py",
            worker_module="apps/worker/tcgscan_worker/catalog/yugioh.py",
            notes="YGOPRODeck public API — no key required. Cached in Redis on diagnostic probes.",
        ),
        _catalog_game_status(
            "one_piece",
            api_module="apps/api/tcgscan_api/sources/one_piece.py",
            worker_module="apps/worker/tcgscan_worker/catalog/one_piece.py",
            optional_env=["ONE_PIECE_API_BASE_URL"],
            notes="OPTCG API — no key required. ONE_PIECE_API_BASE_URL optional.",
        ),
        _catalog_game_status(
            "dragon_ball_fusion_world",
            api_module="apps/api/tcgscan_api/sources/dragon_ball_fusion_world.py",
            implementation="not_implemented",
            optional_env=["DRAGON_BALL_FW_BASE_URL"],
            notes="Official Bandai HTML database — clean JSON adapter not implemented yet.",
        ),
        _catalog_game_status(
            "dragon_ball_masters",
            api_module="apps/api/tcgscan_api/sources/dragon_ball_masters.py",
            implementation="not_implemented",
            optional_env=["DRAGON_BALL_MASTERS_BASE_URL"],
            notes="Official Bandai card list — clean JSON adapter not implemented yet.",
        ),
    ]

    return {
        "architecture": {
            "frontend_calls": "FastAPI only (/v1/*)",
            "external_api_calls": "apps/api/sources (diagnostics) + apps/worker (ingest)",
            "api_sources_folder": "apps/api/tcgscan_api/sources/",
            "background_jobs": "Temporal workflows (not Celery)",
        },
        "pricing_sources": sources,
        "catalog_sources": catalog,
        "vercel_env_required": ["NEXT_PUBLIC_API_URL"],
        "worker_service_required": True,
    }


async def test_ebay_connection() -> dict[str, Any]:
    if not _ebay_configured():
        return {
            "status": "missing_env",
            "provider": "ebay",
            "message": "eBay not configured (set EBAY_OAUTH_TOKEN or EBAY_APP_ID+EBAY_CERT_ID)",
            "ok": False,
        }
    try:
        if _env_set("EBAY_OAUTH_TOKEN"):
            token = os.getenv("EBAY_OAUTH_TOKEN", "").strip()
        else:
            import base64

            app_id = os.getenv("EBAY_APP_ID", "").strip()
            cert_id = os.getenv("EBAY_CERT_ID", "").strip()
            auth = base64.b64encode(f"{app_id}:{cert_id}".encode()).decode()
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    "https://api.ebay.com/identity/v1/oauth2/token",
                    headers={
                        "Authorization": f"Basic {auth}",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    data={
                        "grant_type": "client_credentials",
                        "scope": "https://api.ebay.com/oauth/api_scope",
                    },
                )
                resp.raise_for_status()
                token = str(resp.json().get("access_token", ""))
        if not token:
            return {
                "status": "failed",
                "provider": "ebay",
                "message": "OAuth succeeded but access_token missing",
                "ok": False,
            }
        marketplace = os.getenv("EBAY_MARKETPLACE_ID", "EBAY_GB")
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://api.ebay.com/buy/browse/v1/item_summary/search",
                params={"q": "pokemon tcg", "limit": 1},
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-EBAY-C-MARKETPLACE-ID": marketplace,
                    "Accept": "application/json",
                },
            )
            resp.raise_for_status()
        return {
            "status": "success",
            "provider": "ebay",
            "message": "Browse API search succeeded",
            "marketplace": marketplace,
            "ok": True,
        }
    except Exception as exc:
        log.warning("source_audit.ebay_test_failed", error=str(exc))
        return {"status": "failed", "provider": "ebay", "message": str(exc), "ok": False}


async def test_pokemon_connection() -> dict[str, Any]:
    headers: dict[str, str] = {}
    if _env_set("POKEMONTCG_API_KEY"):
        headers["X-Api-Key"] = os.getenv("POKEMONTCG_API_KEY", "").strip()
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                "https://api.pokemontcg.io/v2/cards",
                params={"pageSize": 1},
                headers=headers,
            )
            resp.raise_for_status()
        return {
            "status": "success",
            "provider": "pokemontcg",
            "message": "pokemontcg.io reachable",
            "api_key_set": _env_set("POKEMONTCG_API_KEY"),
            "ok": True,
        }
    except Exception as exc:
        return {
            "status": "failed",
            "provider": "pokemontcg",
            "message": str(exc),
            "api_key_set": _env_set("POKEMONTCG_API_KEY"),
            "ok": False,
        }


async def test_scryfall_connection() -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                "https://api.scryfall.com/cards/named",
                params={"fuzzy": "Lightning Bolt"},
                headers={"User-Agent": "tcgscan/0.0.0", "Accept": "application/json"},
            )
            resp.raise_for_status()
        return {"status": "success", "provider": "scryfall", "message": "Scryfall reachable", "ok": True}
    except Exception as exc:
        return {"status": "failed", "provider": "scryfall", "message": str(exc), "ok": False}


async def test_ygopro_connection() -> dict[str, Any]:
    client = YgoProDeckClient()
    try:
        return await client.diagnostic()
    finally:
        await client.aclose()


async def test_one_piece_connection() -> dict[str, Any]:
    client = OnePieceClient()
    try:
        return await client.diagnostic()
    finally:
        await client.aclose()


async def test_dragon_ball_fusion_world_connection() -> dict[str, Any]:
    client = DragonBallFusionWorldClient()
    try:
        return await client.diagnostic()
    finally:
        await client.aclose()


async def test_dragon_ball_masters_connection() -> dict[str, Any]:
    client = DragonBallMastersClient()
    try:
        return await client.diagnostic()
    finally:
        await client.aclose()


async def test_reddit_connection() -> dict[str, Any]:
    if not _reddit_configured():
        return {
            "status": "not_implemented",
            "provider": "reddit",
            "message": "Reddit integration not implemented; env vars alone are insufficient",
            "implementation": "missing",
            "ok": False,
        }
    return {
        "status": "not_implemented",
        "provider": "reddit",
        "message": "Reddit client not implemented in worker yet",
        "implementation": "missing",
        "ok": False,
    }


async def test_cardmarket_connection() -> dict[str, Any]:
    if _cardmarket_official_configured():
        return {
            "status": "partial",
            "provider": "cardmarket",
            "message": "Official Cardmarket credentials present but no client implemented",
            "path": "official",
            "ok": False,
        }
    if not _apify_cardmarket_enabled():
        return {
            "status": "missing_env",
            "provider": "cardmarket",
            "message": "Apify fallback disabled (APIFY_TOKEN not set)",
            "ok": False,
        }
    dataset_id = os.getenv("APIFY_CARDMARKET_DATASET_ID", "cardmarket-trend").strip()
    token = os.getenv("APIFY_TOKEN", "").strip()
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                f"https://api.apify.com/v2/datasets/{dataset_id}/items",
                params={"limit": 1, "clean": "true"},
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code == 404:
                return {
                    "status": "failed",
                    "provider": "cardmarket",
                    "message": f"Apify dataset not found: {dataset_id}",
                    "dataset_id": dataset_id,
                    "ok": False,
                }
            resp.raise_for_status()
        items = resp.json()
        count = len(items) if isinstance(items, list) else 0
        return {
            "status": "success",
            "provider": "cardmarket",
            "message": f"Apify dataset reachable ({count} sample items)",
            "dataset_id": dataset_id,
            "ok": True,
        }
    except Exception as exc:
        return {
            "status": "failed",
            "provider": "cardmarket",
            "message": str(exc),
            "dataset_id": dataset_id,
            "ok": False,
        }
