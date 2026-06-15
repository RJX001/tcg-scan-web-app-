"""Stripe checkout + webhook handling."""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from fastapi import Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from tcgscan_api.config import get_settings
from tcgscan_api.db.models import UserTier
from tcgscan_api.errors import AppError
from tcgscan_api.middleware.auth import AuthUser
from tcgscan_api.repositories.users import UsersRepo
from tcgscan_api.services.auth_ctx import resolve_db_user

log = structlog.get_logger()


ALLOWED_COMPS_DAYS = (7, 30, 90, 180)


class AccountOut(BaseModel):
    clerk_id: str
    email: str | None = None
    tier: str
    role: str = "user"
    account_number: str | None = None
    portfolio_limit: int | None = None
    scans_per_day: int | None = None
    comps_days: int = 30


class AccountPreferencesIn(BaseModel):
    comps_days: int


class CheckoutOut(BaseModel):
    url: str


def _stripe() -> Any:
    settings = get_settings()
    if not settings.stripe_secret_key:
        raise AppError("Stripe is not configured", status_code=503)
    try:
        import stripe
    except ImportError as exc:
        raise AppError("stripe package not installed", status_code=503) from exc
    stripe.api_key = settings.stripe_secret_key
    return stripe


async def get_account(session: AsyncSession, request: Request) -> AccountOut:
    auth = await resolve_db_user(session, request)
    settings = get_settings()
    from tcgscan_api.services.auth_ctx import is_pro

    user_row = await UsersRepo(session).get_by_id(auth.id)
    comps_days = user_row.comps_days if user_row is not None else 30

    return AccountOut(
        clerk_id=auth.clerk_id,
        email=auth.email,
        tier=auth.tier,
        role=auth.role,
        account_number=user_row.account_number if user_row is not None else None,
        portfolio_limit=None if is_pro(auth) else settings.free_portfolio_limit,
        scans_per_day=None if is_pro(auth) else settings.free_scans_per_day,
        comps_days=comps_days,
    )


async def update_account_preferences(
    session: AsyncSession, request: Request, body: AccountPreferencesIn
) -> AccountOut:
    auth = await resolve_db_user(session, request)
    from tcgscan_api.services.tier import require_pro

    require_pro(auth, feature="Custom comp window")
    if body.comps_days not in ALLOWED_COMPS_DAYS:
        raise AppError(
            f"comps_days must be one of {list(ALLOWED_COMPS_DAYS)}",
            status_code=400,
        )
    updated = await UsersRepo(session).set_comps_days(auth.id, body.comps_days)
    if updated is None:
        raise AppError("User not found", status_code=404)
    return await get_account(session, request)


async def create_checkout_session(session: AsyncSession, auth: AuthUser) -> CheckoutOut:
    settings = get_settings()
    if not settings.stripe_pro_price_id:
        raise AppError("STRIPE_PRO_PRICE_ID not configured", status_code=503)
    stripe = _stripe()
    user_row = await UsersRepo(session).get_by_id(auth.id)
    if user_row is None:
        raise AppError("User not found", status_code=404)
    customer_id = user_row.stripe_customer_id
    if not customer_id:
        customer = stripe.Customer.create(
            metadata={
                "clerk_id": auth.clerk_id or "",
                "supabase_user_id": auth.supabase_user_id or "",
                "user_id": str(user_row.id),
            },
            email=user_row.email,
        )
        customer_id = customer.id
        await UsersRepo(session).set_stripe_customer(user_row.id, customer_id)

    checkout = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        line_items=[{"price": settings.stripe_pro_price_id, "quantity": 1}],
        success_url=settings.stripe_success_url,
        cancel_url=settings.stripe_cancel_url,
        metadata={"user_id": str(user_row.id)},
    )
    if not checkout.url:
        raise AppError("Stripe checkout URL missing", status_code=502)
    return CheckoutOut(url=checkout.url)


async def create_portal_session(session: AsyncSession, auth: AuthUser) -> CheckoutOut:
    stripe = _stripe()
    user_row = await UsersRepo(session).get_by_id(auth.id)
    if user_row is None:
        raise AppError("User not found", status_code=404)
    if not user_row.stripe_customer_id:
        raise AppError("No billing account — subscribe first", status_code=400)
    portal = stripe.billing_portal.Session.create(
        customer=user_row.stripe_customer_id,
        return_url=settings_success_url(),
    )
    return CheckoutOut(url=portal.url)


def settings_success_url() -> str:
    return get_settings().stripe_success_url.split("?")[0]


async def handle_stripe_webhook(
    session: AsyncSession, payload: bytes, sig_header: str | None
) -> None:
    settings = get_settings()
    if not settings.stripe_webhook_secret:
        raise AppError("Webhook secret not configured", status_code=503)
    stripe = _stripe()
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.stripe_webhook_secret)
    except Exception as exc:
        raise AppError(f"Invalid webhook: {exc}", status_code=400) from exc

    etype = event["type"]
    data = event["data"]["object"]
    log.info("stripe.webhook", type=etype)

    if etype in (
        "checkout.session.completed",
        "customer.subscription.created",
        "customer.subscription.updated",
    ):
        user_id = _user_id_from_metadata(data)
        if user_id:
            await UsersRepo(session).set_tier(user_id, UserTier.pro)
    elif etype in ("customer.subscription.deleted",):
        user_id = await _user_id_from_customer(session, data.get("customer"))
        if user_id:
            await UsersRepo(session).set_tier(user_id, UserTier.free)


def _user_id_from_metadata(data: dict[str, object]) -> uuid.UUID | None:
    meta = data.get("metadata") or {}
    if isinstance(meta, dict):
        raw = meta.get("user_id")
        if raw:
            try:
                return uuid.UUID(str(raw))
            except ValueError:
                return None
    return None


async def _user_id_from_customer(session: AsyncSession, customer_id: object) -> uuid.UUID | None:
    if not customer_id:
        return None
    user = await UsersRepo(session).get_by_stripe_customer(str(customer_id))
    return user.id if user else None
