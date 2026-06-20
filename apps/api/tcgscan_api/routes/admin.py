"""Admin API routes — owner dashboard surface."""

from __future__ import annotations

import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from tcgscan_api import __version__
from tcgscan_api.db.models import UserRole, UserTier
from tcgscan_api.db.session import get_session
from tcgscan_api.middleware.auth import AuthUser
from tcgscan_api.repositories.admin import AdminRepo
from tcgscan_api.repositories.users import UsersRepo
from tcgscan_api.services.auth_ctx import resolve_db_user
from tcgscan_api.services.cache import get_redis
from tcgscan_api.services.qdrant import get_qdrant
from tcgscan_api.services.roles import require_admin, require_owner, require_senior
from tcgscan_api.services.admin_sources_status import get_admin_sources_status
from tcgscan_api.services.catalogue_ingest import run_catalogue_ingest
from tcgscan_api.services.catalogue_import import start_full_catalogue_import
from tcgscan_api.services.ebay_ingest import run_ebay_ingest
from tcgscan_api.services.source_audit import (
    test_cardmarket_connection,
    test_dragon_ball_fusion_world_connection,
    test_dragon_ball_masters_connection,
    test_ebay_connection,
    test_one_piece_connection,
    test_pokemon_connection,
    test_reddit_connection,
    test_scryfall_connection,
    test_ygopro_connection,
)

router = APIRouter(prefix="/admin", tags=["admin"])

_APP_STARTED_AT = time.time()


class SetRoleIn(BaseModel):
    role: str = Field(pattern=r"^(user|admin|admin_senior|owner)$")


class SetTierIn(BaseModel):
    tier: str = Field(pattern=r"^(free|pro)$")


class SetAccountNumberIn(BaseModel):
    account_number: str = Field(min_length=1, max_length=16)


class AdminUsersOut(BaseModel):
    items: list[dict[str, Any]]
    total: int
    limit: int
    offset: int


async def _admin_user(request: Request, session: AsyncSession) -> AuthUser:
    user = await resolve_db_user(session, request)
    require_admin(user)
    return user


@router.get("/overview")
async def admin_overview(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    await _admin_user(request, session)
    return await AdminRepo(session).overview()


@router.get("/users", response_model=AdminUsersOut)
async def admin_users(
    request: Request,
    session: AsyncSession = Depends(get_session),
    limit: int = 50,
    offset: int = 0,
    q: str | None = None,
) -> AdminUsersOut:
    await _admin_user(request, session)
    items, total = await AdminRepo(session).list_users(limit=limit, offset=offset, q=q)
    return AdminUsersOut(items=items, total=total, limit=limit, offset=offset)


@router.get("/users/{user_id}")
async def admin_user_detail(
    user_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    await _admin_user(request, session)
    detail = await AdminRepo(session).user_detail(user_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="User not found")
    return detail


@router.post("/users/{user_id}/role")
async def admin_set_role(
    user_id: uuid.UUID,
    body: SetRoleIn,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    actor = await resolve_db_user(session, request)
    require_owner(actor)
    if actor.id == user_id and body.role != UserRole.owner.value:
        raise HTTPException(status_code=403, detail="Owner cannot demote themselves")
    repo = UsersRepo(session)
    target = await repo.get_by_id(user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    role = UserRole(body.role)
    updated = await repo.set_role(user_id, role)
    assert updated is not None
    return {"role": updated.role.value}


@router.post("/users/{user_id}/account-number")
async def admin_set_account_number(
    user_id: uuid.UUID,
    body: SetAccountNumberIn,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    actor = await resolve_db_user(session, request)
    require_owner(actor)
    repo = UsersRepo(session)
    target = await repo.get_by_id(user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    if await repo.account_number_taken(body.account_number, exclude_id=user_id):
        raise HTTPException(status_code=409, detail="Account number already in use")
    updated = await repo.set_account_number(user_id, body.account_number)
    assert updated is not None
    return {"account_number": updated.account_number}


@router.post("/users/{user_id}/tier")
async def admin_set_tier(
    user_id: uuid.UUID,
    body: SetTierIn,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    actor = await resolve_db_user(session, request)
    require_senior(actor)
    repo = UsersRepo(session)
    target = await repo.get_by_id(user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    await repo.set_tier(user_id, UserTier(body.tier))
    return {"tier": body.tier}


@router.get("/revenue")
async def admin_revenue(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    actor = await resolve_db_user(session, request)
    require_senior(actor)
    return await AdminRepo(session).revenue()


@router.get("/data-health")
async def admin_data_health(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    await _admin_user(request, session)
    return await AdminRepo(session).data_health()


@router.get("/sources/status")
async def admin_sources_status(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    await _admin_user(request, session)
    return await get_admin_sources_status(session)


async def _run_ingest(
    request: Request,
    session: AsyncSession,
    source_key: str,
    *,
    limit: int,
    dry_run: bool,
) -> dict[str, Any]:
    await _admin_user(request, session)
    result = await run_catalogue_ingest(session, source_key, limit=limit, dry_run=dry_run)
    return {
        "source_run_id": result.source_run_id,
        "status": result.status,
        "inserted_count": result.inserted_count,
        "updated_count": result.updated_count,
        "skipped_count": result.skipped_count,
        "message": result.message,
        "dry_run": result.dry_run,
    }


@router.post("/sources/ingest/pokemon")
async def admin_ingest_pokemon(
    request: Request,
    session: AsyncSession = Depends(get_session),
    limit: int = Query(default=100, ge=1, le=5000),
    dry_run: bool = Query(default=False),
) -> dict[str, Any]:
    return await _run_ingest(request, session, "pokemon", limit=limit, dry_run=dry_run)


@router.post("/sources/ingest/scryfall")
async def admin_ingest_scryfall(
    request: Request,
    session: AsyncSession = Depends(get_session),
    limit: int = Query(default=100, ge=1, le=5000),
    dry_run: bool = Query(default=False),
) -> dict[str, Any]:
    return await _run_ingest(request, session, "scryfall", limit=limit, dry_run=dry_run)


@router.post("/sources/ingest/ygopro")
async def admin_ingest_ygopro(
    request: Request,
    session: AsyncSession = Depends(get_session),
    limit: int = Query(default=100, ge=1, le=5000),
    dry_run: bool = Query(default=False),
) -> dict[str, Any]:
    return await _run_ingest(request, session, "ygopro", limit=limit, dry_run=dry_run)


@router.post("/sources/ingest/one-piece")
async def admin_ingest_one_piece(
    request: Request,
    session: AsyncSession = Depends(get_session),
    limit: int = Query(default=100, ge=1, le=5000),
    dry_run: bool = Query(default=False),
) -> dict[str, Any]:
    return await _run_ingest(request, session, "one_piece", limit=limit, dry_run=dry_run)


@router.post("/sources/ingest/dragon-ball-fusion-world")
async def admin_ingest_dragon_ball_fw(
    request: Request,
    session: AsyncSession = Depends(get_session),
    limit: int = Query(default=100, ge=1, le=5000),
    dry_run: bool = Query(default=False),
) -> dict[str, Any]:
    return await _run_ingest(request, session, "dragon_ball_fusion_world", limit=limit, dry_run=dry_run)


@router.post("/sources/ingest/dragon-ball-masters")
async def admin_ingest_dragon_ball_masters(
    request: Request,
    session: AsyncSession = Depends(get_session),
    limit: int = Query(default=100, ge=1, le=5000),
    dry_run: bool = Query(default=False),
) -> dict[str, Any]:
    return await _run_ingest(request, session, "dragon_ball_masters", limit=limit, dry_run=dry_run)


async def _run_import(
    request: Request,
    session: AsyncSession,
    source_key: str,
    *,
    limit: int | None,
    dry_run: bool,
    force: bool,
    batch_size: int | None = None,
    page_token: str | None = None,
    source_run_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    await _admin_user(request, session)
    result = await start_full_catalogue_import(
        session,
        source_key,
        limit=limit,
        dry_run=dry_run,
        force=force,
        batch_size=batch_size,
        page_token=page_token,
        source_run_id=source_run_id,
    )
    return {
        "source_run_id": result.source_run_id,
        "status": result.status,
        "inserted_count": result.inserted_count,
        "updated_count": result.updated_count,
        "skipped_count": result.skipped_count,
        "message": result.message,
        "dry_run": result.dry_run,
        "next_page_token": result.next_page_token,
        "complete": result.complete,
    }


@router.post("/sources/import/pokemon")
async def admin_import_pokemon(
    request: Request,
    session: AsyncSession = Depends(get_session),
    limit: int | None = Query(default=None, ge=1, le=50000),
    dry_run: bool = Query(default=False),
    force: bool = Query(default=False),
    batch_size: int = Query(default=250, ge=1, le=250),
    page_token: str | None = Query(default=None),
    source_run_id: uuid.UUID | None = Query(default=None),
) -> dict[str, Any]:
    return await _run_import(
        request,
        session,
        "pokemon",
        limit=limit,
        dry_run=dry_run,
        force=force,
        batch_size=batch_size,
        page_token=page_token,
        source_run_id=source_run_id,
    )


@router.post("/sources/import/scryfall")
async def admin_import_scryfall(
    request: Request,
    session: AsyncSession = Depends(get_session),
    limit: int | None = Query(default=None, ge=1, le=50000),
    dry_run: bool = Query(default=False),
    force: bool = Query(default=False),
) -> dict[str, Any]:
    return await _run_import(request, session, "scryfall", limit=limit, dry_run=dry_run, force=force)


@router.post("/sources/import/ygopro")
async def admin_import_ygopro(
    request: Request,
    session: AsyncSession = Depends(get_session),
    limit: int | None = Query(default=None, ge=1, le=50000),
    dry_run: bool = Query(default=False),
    force: bool = Query(default=False),
) -> dict[str, Any]:
    return await _run_import(request, session, "ygopro", limit=limit, dry_run=dry_run, force=force)


@router.post("/sources/import/one-piece")
async def admin_import_one_piece(
    request: Request,
    session: AsyncSession = Depends(get_session),
    limit: int | None = Query(default=None, ge=1, le=50000),
    dry_run: bool = Query(default=False),
    force: bool = Query(default=False),
) -> dict[str, Any]:
    return await _run_import(request, session, "one_piece", limit=limit, dry_run=dry_run, force=force)


@router.post("/sources/ingest/ebay")
async def admin_ingest_ebay(
    request: Request,
    session: AsyncSession = Depends(get_session),
    query: str = Query(default="pokemon card charizard", max_length=200),
    limit: int = Query(default=25, ge=1, le=100),
    dry_run: bool = Query(default=False),
) -> dict[str, Any]:
    await _admin_user(request, session)
    result = await run_ebay_ingest(session, query=query, limit=limit, dry_run=dry_run)
    return {
        "source_run_id": result.source_run_id,
        "status": result.status,
        "inserted_count": result.inserted_count,
        "updated_count": result.updated_count,
        "skipped_count": result.skipped_count,
        "message": result.message,
        "dry_run": result.dry_run,
    }


@router.get("/sources/test/ebay")
async def admin_test_ebay(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    await _admin_user(request, session)
    return await test_ebay_connection()


@router.get("/sources/test/pokemon")
async def admin_test_pokemon(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    await _admin_user(request, session)
    return await test_pokemon_connection()


@router.get("/sources/test/scryfall")
async def admin_test_scryfall(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    await _admin_user(request, session)
    return await test_scryfall_connection()


@router.get("/sources/test/ygopro")
async def admin_test_ygopro(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    await _admin_user(request, session)
    return await test_ygopro_connection()


@router.get("/sources/test/one-piece")
async def admin_test_one_piece(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    await _admin_user(request, session)
    return await test_one_piece_connection()


@router.get("/sources/test/dragon-ball-fusion-world")
async def admin_test_dragon_ball_fusion_world(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    await _admin_user(request, session)
    return await test_dragon_ball_fusion_world_connection()


@router.get("/sources/test/dragon-ball-masters")
async def admin_test_dragon_ball_masters(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    await _admin_user(request, session)
    return await test_dragon_ball_masters_connection()


@router.get("/sources/test/reddit")
async def admin_test_reddit(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    await _admin_user(request, session)
    return await test_reddit_connection()


@router.get("/sources/test/cardmarket")
async def admin_test_cardmarket(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    await _admin_user(request, session)
    return await test_cardmarket_connection()


@router.get("/system")
async def admin_system(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    await _admin_user(request, session)
    admin_repo = AdminRepo(session)
    db_ok = await admin_repo.db_reachable()

    redis_ok = False
    try:
        r = get_redis()
        ping = r.ping()
        if hasattr(ping, "__await__"):
            ping = await ping
        redis_ok = bool(ping)
        await r.aclose()
    except Exception:
        redis_ok = False

    qdrant_ok = False
    try:
        qc = get_qdrant()
        await qc.get_collections()
        qdrant_ok = True
        await qc.close()
    except Exception:
        qdrant_ok = False

    return {
        "db_reachable": db_ok,
        "redis_reachable": redis_ok,
        "qdrant_reachable": qdrant_ok,
        "api_version": __version__,
        "uptime_seconds": int(time.time() - _APP_STARTED_AT),
    }
