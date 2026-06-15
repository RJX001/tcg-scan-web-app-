"""Admin diagnostics for external data source configuration (never returns secret values)."""

from __future__ import annotations

import os
from typing import Any

import httpx
import structlog

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


def _catalog_game_status(game: str) -> dict[str, Any]:
    env_by_game: dict[str, list[str]] = {
        "pokemon": ["POKEMONTCG_API_KEY"],
        "mtg": [],
        "yugioh": [],
        "one_piece": [],
        "lorcana": [],
        "sports": ["TCG_API_KEY"],
    }
    module_by_game: dict[str, str] = {
        "pokemon": "apps/worker/tcgscan_worker/catalog/pokemon.py",
        "mtg": "apps/worker/tcgscan_worker/catalog/mtg.py",
        "yugioh": "apps/worker/tcgscan_worker/catalog/yugioh.py",
        "one_piece": "apps/worker/tcgscan_worker/catalog/one_piece.py",
        "lorcana": "apps/worker/tcgscan_worker/catalog/lorcana.py",
        "sports": "apps/worker/tcgscan_worker/catalog/sports.py",
    }
    optional = env_by_game.get(game, [])
    configured = all(_env_set(name) for name in optional) if optional else True
    return {
        "id": game,
        "type": "catalog",
        "implementation": "working" if game in module_by_game else "missing",
        "configured": configured,
        "optional_env": _env_flags(optional),
        "worker_module": module_by_game.get(game),
        "ingest_command": f"pnpm ingest:catalog -- --game {game}",
        "schedule": f"catalog-weekly-{game} (Temporal)",
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
            "implementation": "partial",
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
                "Official Browse API only. EPN affiliate tagging not implemented — "
                "listing URLs stored/served without campid. EBAY_DEV_ID unused in code."
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
            "notes": (
                "Apify dataset poll only (no actor runner). Official Cardmarket OAuth env vars "
                "not read by current code. Disabled when APIFY_TOKEN missing."
            ),
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
            "notes": "Not implemented. Intended for hype/sentiment only — not card metadata or prices.",
        },
    ]

    catalog = [_catalog_game_status(game) for game in ("pokemon", "mtg", "yugioh", "one_piece")]

    return {
        "architecture": {
            "frontend_calls": "FastAPI only (/v1/*)",
            "external_api_calls": "apps/worker (Temporal + CLI ingest)",
            "api_sources_folder": "none — use apps/worker/tcgscan_worker/sources and catalog/",
            "background_jobs": "Temporal workflows (not Celery)",
        },
        "pricing_sources": sources,
        "catalog_sources": catalog,
        "vercel_env_required": ["NEXT_PUBLIC_API_URL"],
        "worker_service_required": True,
    }


async def test_ebay_connection() -> dict[str, Any]:
    if not _ebay_configured():
        return {"ok": False, "message": "eBay not configured (set EBAY_OAUTH_TOKEN or EBAY_APP_ID+EBAY_CERT_ID)"}
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
            return {"ok": False, "message": "OAuth succeeded but access_token missing"}
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
        return {"ok": True, "message": "Browse API search succeeded", "marketplace": marketplace}
    except Exception as exc:
        log.warning("source_audit.ebay_test_failed", error=str(exc))
        return {"ok": False, "message": str(exc)}


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
        return {"ok": True, "message": "pokemontcg.io reachable", "api_key_set": _env_set("POKEMONTCG_API_KEY")}
    except Exception as exc:
        return {"ok": False, "message": str(exc), "api_key_set": _env_set("POKEMONTCG_API_KEY")}


async def test_scryfall_connection() -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                "https://api.scryfall.com/cards/named",
                params={"fuzzy": "Lightning Bolt"},
                headers={"User-Agent": "tcgscan/0.0.0", "Accept": "application/json"},
            )
            resp.raise_for_status()
        return {"ok": True, "message": "Scryfall reachable"}
    except Exception as exc:
        return {"ok": False, "message": str(exc)}


async def test_ygopro_connection() -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                "https://db.ygoprodeck.com/api/v7/cardinfo.php",
                params={"name": "Dark Magician"},
            )
            resp.raise_for_status()
            data = resp.json()
        count = len(data.get("data") or [])
        return {"ok": True, "message": f"YGOPRODeck reachable ({count} cards matched)"}
    except Exception as exc:
        return {"ok": False, "message": str(exc)}


async def test_one_piece_connection() -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get("https://optcgapi.com/api/allCards/")
            resp.raise_for_status()
            data = resp.json()
        count = len(data.get("data") or [])
        return {"ok": True, "message": f"OPTCG API reachable ({count} cards)"}
    except Exception as exc:
        return {"ok": False, "message": str(exc)}


async def test_reddit_connection() -> dict[str, Any]:
    if not _reddit_configured():
        return {
            "ok": False,
            "message": "Reddit integration not implemented; env vars alone are insufficient",
            "implementation": "missing",
        }
    return {
        "ok": False,
        "message": "Reddit client not implemented in worker yet",
        "implementation": "missing",
    }


async def test_cardmarket_connection() -> dict[str, Any]:
    if _cardmarket_official_configured():
        return {
            "ok": False,
            "message": "Official Cardmarket credentials present but no client implemented",
            "path": "official",
        }
    if not _apify_cardmarket_enabled():
        return {"ok": False, "message": "Apify fallback disabled (APIFY_TOKEN not set)"}
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
                return {"ok": False, "message": f"Apify dataset not found: {dataset_id}"}
            resp.raise_for_status()
        items = resp.json()
        count = len(items) if isinstance(items, list) else 0
        return {"ok": True, "message": f"Apify dataset reachable ({count} sample items)", "dataset_id": dataset_id}
    except Exception as exc:
        return {"ok": False, "message": str(exc), "dataset_id": dataset_id}
