"""Saved ladder searches — Pro feature, parity with Card Ladder saved searches."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from tcgscan_api.errors import NotFoundError
from tcgscan_api.middleware.auth import AuthUser
from tcgscan_api.repositories.users import SavedSearchRepo
from tcgscan_api.services.tier import require_pro


class SavedSearchParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    game: str | None = None
    q: str | None = None
    sort: str | None = None
    days: int | None = None
    grade: str | None = None


class SavedSearchCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    params: SavedSearchParams


class SavedSearchOut(BaseModel):
    id: str
    name: str
    params: SavedSearchParams
    created_at: str


async def list_saved_searches(session: AsyncSession, user: AuthUser) -> list[SavedSearchOut]:
    rows = await SavedSearchRepo(session).list_for_user(user.id)
    return [
        SavedSearchOut(
            id=str(r.id),
            name=r.name,
            params=SavedSearchParams.model_validate(r.params),
            created_at=r.created_at.isoformat(),
        )
        for r in rows
    ]


async def create_saved_search(
    session: AsyncSession, user: AuthUser, body: SavedSearchCreateIn
) -> SavedSearchOut:
    require_pro(user, feature="Saved searches")
    row = await SavedSearchRepo(session).upsert(
        user_id=user.id,
        name=body.name.strip(),
        params=body.params.model_dump(exclude_none=True),
    )
    return SavedSearchOut(
        id=str(row.id),
        name=row.name,
        params=SavedSearchParams.model_validate(row.params),
        created_at=row.created_at.isoformat(),
    )


async def delete_saved_search(session: AsyncSession, user: AuthUser, search_id: uuid.UUID) -> None:
    deleted = await SavedSearchRepo(session).delete(user.id, search_id)
    if not deleted:
        raise NotFoundError(f"saved search not found: {search_id}")
