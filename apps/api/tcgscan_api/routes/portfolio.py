from __future__ import annotations

import csv
import io
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from tcgscan_api.db.session import get_session
from tcgscan_api.errors import NotFoundError
from tcgscan_api.services.auth_ctx import resolve_db_user
from tcgscan_api.services.portfolio import (
    AlertCreateIn,
    AlertOut,
    PortfolioAddIn,
    PortfolioItemOut,
    PortfolioSummaryOut,
    add_portfolio_item,
    create_alert,
    delete_alert,
    list_alerts,
    list_portfolio,
    portfolio_summary,
    remove_portfolio_item,
)

router = APIRouter(tags=["portfolio"])


@router.get("/portfolio", response_model=list[PortfolioItemOut])
async def get_portfolio(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> list[PortfolioItemOut]:
    auth = await resolve_db_user(session, request)
    return await list_portfolio(session, auth)


@router.get("/portfolio/summary", response_model=PortfolioSummaryOut)
async def get_portfolio_summary(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> PortfolioSummaryOut:
    auth = await resolve_db_user(session, request)
    return await portfolio_summary(session, auth)


@router.get("/portfolio/export")
async def export_portfolio(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    auth = await resolve_db_user(session, request)
    items = await list_portfolio(session, auth)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "name",
            "game",
            "set",
            "number",
            "quantity",
            "cost_basis_usd",
            "estimated_value_usd",
            "slug",
        ]
    )
    for item in items:
        writer.writerow(
            [
                item.card.name,
                item.card.game,
                item.card.set_name or item.card.set_code or "",
                item.card.number or "",
                item.quantity,
                item.cost_basis_usd or "",
                item.estimated_value_usd or "",
                item.card.slug,
            ]
        )
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="tcgscan-portfolio.csv"'},
    )


@router.post("/portfolio", response_model=PortfolioItemOut, status_code=201)
async def post_portfolio(
    body: PortfolioAddIn,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> PortfolioItemOut:
    auth = await resolve_db_user(session, request)
    try:
        return await add_portfolio_item(session, auth, body)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc


@router.delete("/portfolio/{item_id}", status_code=204)
async def delete_portfolio(
    item_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> None:
    auth = await resolve_db_user(session, request)
    try:
        await remove_portfolio_item(session, auth, item_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc


@router.get("/alerts", response_model=list[AlertOut])
async def get_alerts(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> list[AlertOut]:
    auth = await resolve_db_user(session, request)
    return await list_alerts(session, auth)


@router.post("/alerts", response_model=AlertOut, status_code=201)
async def post_alert(
    body: AlertCreateIn,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> AlertOut:
    auth = await resolve_db_user(session, request)
    try:
        return await create_alert(session, auth, body)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc


@router.delete("/alerts/{alert_id}", status_code=204)
async def delete_alert_route(
    alert_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> None:
    auth = await resolve_db_user(session, request)
    try:
        await delete_alert(session, auth, alert_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
