"""Add supabase_user_id to users; make clerk_id nullable.

Revision ID: 0008_supabase_user_id
Revises: 0007_user_role
Create Date: 2026-06-15

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008_supabase_user_id"
down_revision: str | None = "0007_user_role"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("supabase_user_id", sa.String(36), nullable=True))
    op.create_index("ix_users_supabase_user_id", "users", ["supabase_user_id"], unique=True)
    op.alter_column("users", "clerk_id", existing_type=sa.String(128), nullable=True)


def downgrade() -> None:
    op.alter_column("users", "clerk_id", existing_type=sa.String(128), nullable=False)
    op.drop_index("ix_users_supabase_user_id", table_name="users")
    op.drop_column("users", "supabase_user_id")
