"""watchlist_items

Revision ID: 0005_watchlist
Revises: 0004_population_saved_searches
Create Date: 2026-06-11

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_watchlist"
down_revision: str | None = "0004_population_saved_searches"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "watchlist_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("card_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["card_id"], ["card_identity.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "card_id", name="uq_watchlist_user_card"),
    )
    op.create_index("ix_watchlist_items_user_id", "watchlist_items", ["user_id"])
    op.create_index("ix_watchlist_items_card_id", "watchlist_items", ["card_id"])


def downgrade() -> None:
    op.drop_index("ix_watchlist_items_card_id", table_name="watchlist_items")
    op.drop_index("ix_watchlist_items_user_id", table_name="watchlist_items")
    op.drop_table("watchlist_items")
