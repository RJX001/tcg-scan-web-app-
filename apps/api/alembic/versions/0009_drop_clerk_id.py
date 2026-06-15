"""Drop users.clerk_id — Supabase is the sole auth identity.

Revision ID: 0009_drop_clerk_id
Revises: 0008_supabase_user_id
Create Date: 2026-06-15

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009_drop_clerk_id"
down_revision: str | None = "0008_supabase_user_id"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_users_clerk_id", table_name="users")
    op.drop_column("users", "clerk_id")


def downgrade() -> None:
    op.add_column("users", sa.Column("clerk_id", sa.String(128), nullable=True))
    op.create_index("ix_users_clerk_id", "users", ["clerk_id"], unique=True)
