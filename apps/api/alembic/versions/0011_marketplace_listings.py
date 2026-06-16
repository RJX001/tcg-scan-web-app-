"""marketplace_listings table for active marketplace listings

Revision ID: 0011_marketplace_listings
Revises: 0010_catalog_source_runs
Create Date: 2026-06-16

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0011_marketplace_listings"
down_revision: str | None = "0010_catalog_source_runs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "marketplace_listings",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("source_listing_id", sa.String(128), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("price", sa.DECIMAL(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("condition", sa.String(64), nullable=True),
        sa.Column("image_url", sa.String(1024), nullable=True),
        sa.Column("item_url", sa.String(1024), nullable=False),
        sa.Column("seller_username", sa.String(128), nullable=True),
        sa.Column("marketplace", sa.String(32), nullable=False, server_default="EBAY_GB"),
        sa.Column("listing_status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("affiliate_status", sa.String(32), nullable=True),
        sa.Column("grade", sa.String(32), nullable=True),
        sa.Column("raw_metadata", sa.JSON(), nullable=True),
        sa.Column("card_id", sa.UUID(as_uuid=True), sa.ForeignKey("card_identity.id"), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "observed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("source", "source_listing_id", name="uq_marketplace_listing_source_id"),
    )
    op.create_index("ix_marketplace_listings_source", "marketplace_listings", ["source"])
    op.create_index("ix_marketplace_listings_status", "marketplace_listings", ["listing_status"])
    op.create_index("ix_marketplace_listings_observed_at", "marketplace_listings", ["observed_at"])


def downgrade() -> None:
    op.drop_index("ix_marketplace_listings_observed_at", table_name="marketplace_listings")
    op.drop_index("ix_marketplace_listings_status", table_name="marketplace_listings")
    op.drop_index("ix_marketplace_listings_source", table_name="marketplace_listings")
    op.drop_table("marketplace_listings")
