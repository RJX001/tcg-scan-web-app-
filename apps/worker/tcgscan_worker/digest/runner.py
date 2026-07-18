"""Run DigestAgent for Pro users (log-only until email delivery ships)."""

from __future__ import annotations

import structlog
from sqlalchemy import select

from tcgscan_agents.digest_agent.graph import DigestInput, build_digest_graph
from tcgscan_api.db.models import User, UserTier
from tcgscan_worker.db_bridge import session_scope

log = structlog.get_logger()
_graph = build_digest_graph().compile()


async def run_daily_digests() -> int:
    sent = 0
    users_total = 0
    async with session_scope() as session:
        stmt = select(User).where(User.tier == UserTier.pro)
        users = list((await session.execute(stmt)).scalars().all())
        users_total = len(users)
        for user in users:
            from tcgscan_api.repositories.users import PortfolioRepo

            count = len(await PortfolioRepo(session).list_for_user(user.id))
            state = _graph.invoke(
                {
                    "input": DigestInput(user_id=str(user.id), portfolio_count=count),
                    "output": None,
                }
            )
            out = state.get("output")
            if out is None:
                continue
            sent += 1
            log.debug(
                "digest.preview",
                user_id=str(user.id),
                subject=out.subject,
            )
    log.info("digest.run.done", users=users_total, sent=sent)
    return sent
