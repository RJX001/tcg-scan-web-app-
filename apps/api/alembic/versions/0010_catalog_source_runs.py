"""catalog source columns and source_runs table

Revision ID: 0010_catalog_source_runs
Revises: 0009_drop_clerk_id
Create Date: 2026-06-15

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010_catalog_source_runs"
down_revision: str | None = "0009_drop_clerk_id"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("card_identity", sa.Column("source", sa.String(64), nullable=True))
    op.add_column("card_identity", sa.Column("source_card_id", sa.String(128), nullable=True))
    op.create_index("ix_card_identity_source", "card_identity", ["source"])
    op.create_index("ix_card_identity_source_card_id", "card_identity", ["source_card_id"])

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            """
            UPDATE card_identity
            SET source = COALESCE(source, 'seed'),
                source_card_id = COALESCE(
                    source_card_id,
                    NULLIF(number, ''),
                    id::text
                )
            """
        )
    else:
        op.execute(
            """
            UPDATE card_identity
            SET source = COALESCE(source, 'seed'),
                source_card_id = COALESCE(source_card_id, number, id)
            """
        )

    op.create_unique_constraint(
        "uq_card_game_source_id",
        "card_identity",
        ["game", "source", "source_card_id"],
    )

    op.create_table(
        "source_runs",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_key", sa.String(64), nullable=False, index=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("inserted_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.String(1024), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_table("source_runs")
    op.drop_constraint("uq_card_game_source_id", "card_identity", type_="unique")
    op.drop_index("ix_card_identity_source_card_id", table_name="card_identity")
    op.drop_index("ix_card_identity_source", table_name="card_identity")
    op.drop_column("card_identity", "source_card_id")
    op.drop_column("card_identity", "source")
