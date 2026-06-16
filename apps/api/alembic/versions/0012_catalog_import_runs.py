"""extend source_runs for full imports and catalogue search indexes

Revision ID: 0012_catalog_import_runs
Revises: 0011_marketplace_listings
Create Date: 2026-06-16

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0012_catalog_import_runs"
down_revision: str | None = "0011_marketplace_listings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("source_runs", sa.Column("game", sa.String(64), nullable=True))
    op.add_column(
        "source_runs",
        sa.Column("run_type", sa.String(32), nullable=False, server_default="sample"),
    )
    op.create_index("ix_source_runs_run_type", "source_runs", ["run_type"])

    op.create_index("ix_card_identity_rarity", "card_identity", ["rarity"])
    op.create_index("ix_card_identity_updated_at", "card_identity", ["updated_at"])
    op.create_index("ix_card_identity_created_at", "card_identity", ["created_at"])

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE INDEX ix_card_identity_name_lower ON card_identity (lower(name))")
        op.execute(
            "CREATE INDEX ix_card_identity_set_code_lower ON card_identity (lower(set_code))"
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS ix_card_identity_set_code_lower")
        op.execute("DROP INDEX IF EXISTS ix_card_identity_name_lower")

    op.drop_index("ix_card_identity_created_at", table_name="card_identity")
    op.drop_index("ix_card_identity_updated_at", table_name="card_identity")
    op.drop_index("ix_card_identity_rarity", table_name="card_identity")
    op.drop_index("ix_source_runs_run_type", table_name="source_runs")
    op.drop_column("source_runs", "run_type")
    op.drop_column("source_runs", "game")
