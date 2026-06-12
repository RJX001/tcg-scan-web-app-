"""card_population, saved_searches

Revision ID: 0004_population_saved_searches
Revises: 0003_stripe_customer
Create Date: 2026-06-09

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_population_saved_searches"
down_revision: str | None = "0003_stripe_customer"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "card_population",
        sa.Column("card_id", sa.UUID(), nullable=False),
        sa.Column("grade_company", sa.String(16), nullable=False),
        sa.Column("grade", sa.String(16), nullable=False),
        sa.Column("pop_count", sa.Integer(), nullable=False),
        sa.Column(
            "as_of", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["card_id"], ["card_identity.id"]),
        sa.PrimaryKeyConstraint("card_id", "grade_company", "grade"),
    )

    op.create_table(
        "saved_searches",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_saved_search_user_name"),
    )
    op.create_index("ix_saved_searches_user_id", "saved_searches", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_saved_searches_user_id", table_name="saved_searches")
    op.drop_table("saved_searches")
    op.drop_table("card_population")
