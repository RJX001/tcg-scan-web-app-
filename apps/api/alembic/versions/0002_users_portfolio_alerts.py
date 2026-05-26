"""users, portfolio, price_alerts

Revision ID: 0002_users_portfolio_alerts
Revises: 0001_initial
Create Date: 2026-05-26

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_users_portfolio_alerts"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        tier_type = sa.String(16)
        direction_type = sa.String(16)
    else:
        tier_type = sa.String(16)
        direction_type = sa.String(16)

    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("clerk_id", sa.String(128), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("tier", tier_type, nullable=False, server_default="free"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("clerk_id"),
    )
    op.create_index("ix_users_clerk_id", "users", ["clerk_id"])

    op.create_table(
        "portfolio_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("card_id", sa.UUID(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("cost_basis_usd", sa.Numeric(12, 2), nullable=True),
        sa.Column("notes", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["card_id"], ["card_identity.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "card_id", name="uq_portfolio_user_card"),
    )
    op.create_index("ix_portfolio_items_user_id", "portfolio_items", ["user_id"])
    op.create_index("ix_portfolio_items_card_id", "portfolio_items", ["card_id"])

    op.create_table(
        "price_alerts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("card_id", sa.UUID(), nullable=False),
        sa.Column("direction", direction_type, nullable=False),
        sa.Column("threshold_usd", sa.Numeric(12, 2), nullable=False),
        sa.Column("grade_filter", sa.String(16), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["card_id"], ["card_identity.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_price_alerts_user_id", "price_alerts", ["user_id"])
    op.create_index("ix_price_alerts_card_id", "price_alerts", ["card_id"])


def downgrade() -> None:
    op.drop_index("ix_price_alerts_card_id", table_name="price_alerts")
    op.drop_index("ix_price_alerts_user_id", table_name="price_alerts")
    op.drop_table("price_alerts")
    op.drop_index("ix_portfolio_items_card_id", table_name="portfolio_items")
    op.drop_index("ix_portfolio_items_user_id", table_name="portfolio_items")
    op.drop_table("portfolio_items")
    op.drop_index("ix_users_clerk_id", table_name="users")
    op.drop_table("users")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        sa.Enum(name="alert_direction").drop(bind, checkfirst=True)
        sa.Enum(name="user_tier").drop(bind, checkfirst=True)
