from __future__ import annotations

from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from tcgscan_api.db.session import get_session
from tcgscan_api.errors import AppError
from tcgscan_api.middleware.auth import AuthUser
from tcgscan_api.services.auth_ctx import resolve_db_user
from tcgscan_api.services.billing import (
    AccountOut,
    AccountPreferencesIn,
    CheckoutOut,
    create_checkout_session,
    create_portal_session,
    get_account,
    handle_stripe_webhook,
    update_account_preferences,
)

router = APIRouter(tags=["billing"])


def _require_user(request: Request) -> AuthUser:
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return cast(AuthUser, user)


@router.get("/account", response_model=AccountOut)
async def account(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> AccountOut:
    await resolve_db_user(session, request)
    return await get_account(session, request)


@router.get("/me", response_model=AccountOut)
async def me(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> AccountOut:
    return await get_account(session, request)


@router.patch("/account/preferences", response_model=AccountOut)
async def account_preferences(
    body: AccountPreferencesIn,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> AccountOut:
    try:
        return await update_account_preferences(session, request, body)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/billing/checkout", response_model=CheckoutOut)
async def billing_checkout(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> CheckoutOut:
    auth = await resolve_db_user(session, request)
    try:
        return await create_checkout_session(session, auth)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/billing/portal", response_model=CheckoutOut)
async def billing_portal(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> CheckoutOut:
    auth = await resolve_db_user(session, request)
    try:
        return await create_portal_session(session, auth)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/billing/webhook", status_code=204)
async def billing_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> None:
    payload = await request.body()
    sig = request.headers.get("stripe-signature")
    try:
        await handle_stripe_webhook(session, payload, sig)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
