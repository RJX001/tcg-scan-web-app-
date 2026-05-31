from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from tcgscan_api.db.models import CardIdentity, Game


class CardsRepo:
    """Repository for card_identity. Idempotent upserts keyed on (game, set_code, number)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, card_id: uuid.UUID) -> CardIdentity | None:
        return await self._session.get(CardIdentity, card_id)

    async def get_by_external(
        self, game: Game, set_code: str | None, number: str | None
    ) -> CardIdentity | None:
        stmt = select(CardIdentity).where(
            CardIdentity.game == game,
            CardIdentity.set_code == set_code,
            CardIdentity.number == number,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> CardIdentity | None:
        from tcgscan_api.services.slug import parse_card_slug

        try:
            game_str, set_code, number = parse_card_slug(slug)
            game = Game(game_str)
        except (ValueError, KeyError):
            return None
        return await self.get_by_external(game, set_code, number)

    async def search(
        self,
        *,
        q: str,
        game: str | None = None,
        limit: int = 20,
    ) -> list[CardIdentity]:
        pattern = f"%{q.strip()}%"
        stmt = select(CardIdentity).where(
            or_(
                CardIdentity.name.ilike(pattern),
                CardIdentity.set_name.ilike(pattern),
                CardIdentity.set_code.ilike(pattern),
                CardIdentity.number.ilike(pattern),
            )
        )
        if game:
            try:
                stmt = stmt.where(CardIdentity.game == Game(game))
            except ValueError:
                pass
        stmt = stmt.order_by(func.length(CardIdentity.name), CardIdentity.name).limit(limit)
        return list((await self._session.execute(stmt)).scalars().all())

    async def list_by_game(self, game: str, *, limit: int = 5) -> list[CardIdentity]:
        try:
            game_enum = Game(game)
        except ValueError:
            return []
        stmt = (
            select(CardIdentity)
            .where(CardIdentity.game == game_enum)
            .order_by(CardIdentity.name)
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def upsert_many(self, rows: Iterable[dict[str, object]]) -> int:
        """Insert/update many card_identity rows. Returns number processed."""
        items = list(rows)
        if not items:
            return 0

        now = datetime.now()
        for r in items:
            r.setdefault("id", uuid.uuid4())
            r.setdefault("created_at", now)
            r["updated_at"] = now

        dialect = self._session.bind.dialect.name if self._session.bind else "postgresql"
        if dialect == "postgresql":
            stmt = pg_insert(CardIdentity).values(items)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_card_game_set_number",
                set_={
                    "name": stmt.excluded.name,
                    "set_name": stmt.excluded.set_name,
                    "rarity": stmt.excluded.rarity,
                    "variants": stmt.excluded.variants,
                    "attributes": stmt.excluded.attributes,
                    "image_urls": stmt.excluded.image_urls,
                    "external_ids": stmt.excluded.external_ids,
                    "updated_at": stmt.excluded.updated_at,
                },
            )
            await self._session.execute(stmt)
        else:
            for r in items:
                game_val = r["game"]
                game = game_val if isinstance(game_val, Game) else Game(str(game_val))
                set_code = r.get("set_code")
                number = r.get("number")
                existing = await self.get_by_external(
                    game,
                    str(set_code) if set_code is not None else None,
                    str(number) if number is not None else None,
                )
                if existing is None:
                    self._session.add(CardIdentity(**r))
                else:
                    for k, v in r.items():
                        if k in {"id", "created_at"}:
                            continue
                        setattr(existing, k, v)
        await self._session.commit()
        return len(items)