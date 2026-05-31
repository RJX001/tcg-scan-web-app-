"""Daily digest preview via DigestAgent graph."""

from __future__ import annotations

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from tcgscan_agents.digest_agent.graph import DigestInput, build_digest_graph
from tcgscan_api.middleware.auth import AuthUser
from tcgscan_api.repositories.users import PortfolioRepo
from tcgscan_api.services.tier import require_pro


class DigestPreviewOut(BaseModel):
    subject: str
    body: str
    portfolio_count: int


async def preview_digest(session: AsyncSession, auth: AuthUser) -> DigestPreviewOut:
    require_pro(auth, feature="Daily digest")
    items = await PortfolioRepo(session).list_for_user(auth.id)
    inp = DigestInput(user_id=str(auth.id), portfolio_count=len(items))
    graph = build_digest_graph().compile()
    result = graph.invoke({"input": inp, "output": None})
    out = result["output"]
    if out is None:
        return DigestPreviewOut(
            subject="TCG Scan daily brief",
            body="No digest available yet.",
            portfolio_count=len(items),
        )
    return DigestPreviewOut(
        subject=out.subject,
        body=out.body,
        portfolio_count=len(items),
    )
