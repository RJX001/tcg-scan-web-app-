from __future__ import annotations

import uuid

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from tcgscan_api.errors import NotFoundError
from tcgscan_api.middleware.auth import AuthUser
from tcgscan_api.repositories.cards import CardsRepo
from tcgscan_api.repositories.users import PortfolioRepo, UsersRepo
from tcgscan_api.services.cards import CardOut, _to_out, get_comp_summary
from tcgscan_api.services.tier import check_portfolio_limit, require_pro


class PortfolioItemOut(BaseModel):
    id: str
    card: CardOut
    quantity: int
    cost_basis_usd: float | None = None
    notes: str | None = None
    estimated_value_usd: float | None = None


class PortfolioAddIn(BaseModel):
    card_id: str
    quantity: int = Field(default=1, ge=1)
    cost_basis_usd: float | None = None
    notes: str | None = None


class PortfolioSummaryOut(BaseModel):
    item_count: int
    total_quantity: int
    total_cost_basis_usd: float | None = None
    estimated_value_usd: float | None = None


class AlertOut(BaseModel):
    id: str
    card: CardOut
    direction: str
    threshold_usd: float
    grade_filter: str | None = None
    active: bool


class AlertCreateIn(BaseModel):
    card_id: str
    direction: str = Field(pattern="^(below|above)$")
    threshold_usd: float = Field(gt=0)
    grade_filter: str | None = None


async def list_portfolio(session: AsyncSession, auth: AuthUser) -> list[PortfolioItemOut]:
    user_id = auth.id
    items = await PortfolioRepo(session).list_for_user(user_id)
    out: list[PortfolioItemOut] = []
    for item in items:
        card = await CardsRepo(session).get(item.card_id)
        if card is None:
            continue
        summary = await get_comp_summary(session, item.card_id, days=30)
        est = summary.median_usd
        if est is not None:
            est *= item.quantity
        out.append(
            PortfolioItemOut(
                id=str(item.id),
                card=_to_out(card),
                quantity=item.quantity,
                cost_basis_usd=float(item.cost_basis_usd) if item.cost_basis_usd else None,
                notes=item.notes,
                estimated_value_usd=est,
            )
        )
    return out


async def portfolio_summary(session: AsyncSession, auth: AuthUser) -> PortfolioSummaryOut:
    items = await list_portfolio(session, auth)
    total_qty = sum(i.quantity for i in items)
    cost = sum((i.cost_basis_usd or 0) * i.quantity for i in items)
    value = sum(i.estimated_value_usd or 0 for i in items)
    return PortfolioSummaryOut(
        item_count=len(items),
        total_quantity=total_qty,
        total_cost_basis_usd=cost if cost > 0 else None,
        estimated_value_usd=value if value > 0 else None,
    )


async def add_portfolio_item(
    session: AsyncSession, auth: AuthUser, body: PortfolioAddIn
) -> PortfolioItemOut:
    users = UsersRepo(session)
    count = await users.count_portfolio_items(auth.id)
    await check_portfolio_limit(auth, count)

    card_id = uuid.UUID(body.card_id)
    card = await CardsRepo(session).get(card_id)
    if card is None:
        raise NotFoundError(f"card not found: {body.card_id}")
    item = await PortfolioRepo(session).add(
        user_id=auth.id,
        card_id=card_id,
        quantity=body.quantity,
        cost_basis_usd=body.cost_basis_usd,
        notes=body.notes,
    )
    summary = await get_comp_summary(session, card_id, days=30)
    est = summary.median_usd
    if est is not None:
        est *= item.quantity
    return PortfolioItemOut(
        id=str(item.id),
        card=_to_out(card),
        quantity=item.quantity,
        cost_basis_usd=float(item.cost_basis_usd) if item.cost_basis_usd else None,
        notes=item.notes,
        estimated_value_usd=est,
    )


async def remove_portfolio_item(session: AsyncSession, auth: AuthUser, item_id: uuid.UUID) -> None:
    ok = await PortfolioRepo(session).remove(auth.id, item_id)
    if not ok:
        raise NotFoundError(f"portfolio item not found: {item_id}")


async def list_alerts(session: AsyncSession, auth: AuthUser) -> list[AlertOut]:
    from tcgscan_api.repositories.users import AlertsRepo

    alerts = await AlertsRepo(session).list_for_user(auth.id)
    out: list[AlertOut] = []
    for alert in alerts:
        card = await CardsRepo(session).get(alert.card_id)
        if card is None:
            continue
        out.append(
            AlertOut(
                id=str(alert.id),
                card=_to_out(card),
                direction=str(alert.direction.value),
                threshold_usd=float(alert.threshold_usd),
                grade_filter=alert.grade_filter,
                active=alert.active,
            )
        )
    return out


async def create_alert(session: AsyncSession, auth: AuthUser, body: AlertCreateIn) -> AlertOut:
    from tcgscan_api.repositories.users import AlertsRepo

    require_pro(auth, feature="Price alerts")
    card_id = uuid.UUID(body.card_id)
    card = await CardsRepo(session).get(card_id)
    if card is None:
        raise NotFoundError(f"card not found: {body.card_id}")
    alert = await AlertsRepo(session).create(
        user_id=auth.id,
        card_id=card_id,
        direction=body.direction,
        threshold_usd=body.threshold_usd,
        grade_filter=body.grade_filter,
    )
    return AlertOut(
        id=str(alert.id),
        card=_to_out(card),
        direction=str(alert.direction.value),
        threshold_usd=float(alert.threshold_usd),
        grade_filter=alert.grade_filter,
        active=alert.active,
    )


async def delete_alert(session: AsyncSession, auth: AuthUser, alert_id: uuid.UUID) -> None:
    from tcgscan_api.repositories.users import AlertsRepo

    ok = await AlertsRepo(session).delete(auth.id, alert_id)
    if not ok:
        raise NotFoundError(f"alert not found: {alert_id}")
