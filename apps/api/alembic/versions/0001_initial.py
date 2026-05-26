"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-20

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


GAME_VALUES = (
    "pokemon",
    "mtg",
    "yugioh",
    "one_piece",
    "lorcana",
    "star_wars_unlimited",
    "flesh_and_blood",
    "digimon",
    "sports_baseball",
    "sports_basketball",
    "sports_football",
    "sports_soccer",
    "other",
)


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
        game = sa.Enum(*GAME_VALUES, name="game")
        sale_kind = sa.Enum("sold", "listing", name="sale_kind")
        game.create(bind, checkfirst=True)
        sale_kind.create(bind, checkfirst=True)
        game_type: sa.types.TypeEngine = game
        kind_type: sa.types.TypeEngine = sale_kind
    else:
        game_type = sa.String(length=32)
        kind_type = sa.String(length=16)

    op.create_table(
        "card_identity",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True) if dialect == "postgresql" else sa.String(36),
            primary_key=True,
        ),
        sa.Column("game", game_type, nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False, index=True),
        sa.Column("set_code", sa.String(64), index=True),
        sa.Column("set_name", sa.String(255)),
        sa.Column("number", sa.String(32)),
        sa.Column("rarity", sa.String(64)),
        sa.Column("variants", sa.JSON()),
        sa.Column("attributes", sa.JSON()),
        sa.Column("image_urls", sa.JSON()),
        sa.Column("external_ids", sa.JSON()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("game", "set_code", "number", name="uq_card_game_set_number"),
    )

    op.create_table(
        "sale_event",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True) if dialect == "postgresql" else sa.String(36),
            primary_key=True,
        ),
        sa.Column(
            "card_id",
            sa.UUID(as_uuid=True) if dialect == "postgresql" else sa.String(36),
            sa.ForeignKey("card_identity.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("source", sa.String(64), nullable=False, index=True),
        sa.Column("kind", kind_type, nullable=False),
        sa.Column("sold_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("price", sa.DECIMAL(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("price_usd", sa.DECIMAL(12, 2)),
        sa.Column("grade_company", sa.String(16)),
        sa.Column("grade", sa.String(16)),
        sa.Column("condition", sa.String(32)),
        sa.Column("listing_url", sa.String(512)),
        sa.Column("raw_payload", sa.JSON()),
        sa.Column(
            "ingested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("source", "listing_url", "sold_at", name="uq_sale_dedup"),
    )
    op.create_index("ix_sale_card_soldat", "sale_event", ["card_id", "sold_at"])

    op.create_table(
        "card_price_daily",
        sa.Column(
            "card_id",
            sa.UUID(as_uuid=True) if dialect == "postgresql" else sa.String(36),
            sa.ForeignKey("card_identity.id"),
            primary_key=True,
        ),
        sa.Column("day", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("grade_bucket", sa.String(16), primary_key=True),
        sa.Column("sample_count", sa.Integer, nullable=False),
        sa.Column("mean_usd", sa.DECIMAL(12, 2), nullable=False),
        sa.Column("median_usd", sa.DECIMAL(12, 2), nullable=False),
        sa.Column("min_usd", sa.DECIMAL(12, 2), nullable=False),
        sa.Column("max_usd", sa.DECIMAL(12, 2), nullable=False),
    )

    op.create_table(
        "fx_rate",
        sa.Column("day", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("currency", sa.String(3), primary_key=True),
        sa.Column("rate_to_usd", sa.DECIMAL(18, 8), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("fx_rate")
    op.drop_table("card_price_daily")
    op.drop_index("ix_sale_card_soldat", table_name="sale_event")
    op.drop_table("sale_event")
    op.drop_table("card_identity")
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        sa.Enum(name="sale_kind").drop(bind, checkfirst=True)
        sa.Enum(name="game").drop(bind, checkfirst=True)
