from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DECIMAL,
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tcgscan_api.db.session import Base


class Game(str, enum.Enum):
    pokemon = "pokemon"
    mtg = "mtg"
    yugioh = "yugioh"
    one_piece = "one_piece"
    dragon_ball_fusion_world = "dragon_ball_fusion_world"
    dragon_ball_masters = "dragon_ball_masters"
    lorcana = "lorcana"
    star_wars_unlimited = "star_wars_unlimited"
    flesh_and_blood = "flesh_and_blood"
    digimon = "digimon"
    sports_baseball = "sports_baseball"
    sports_basketball = "sports_basketball"
    sports_football = "sports_football"
    sports_soccer = "sports_soccer"
    other = "other"


class SourceRunStatus(str, enum.Enum):
    started = "started"
    success = "success"
    failed = "failed"
    partial = "partial"


class SaleKind(str, enum.Enum):
    sold = "sold"
    listing = "listing"


class CardIdentity(Base):
    __tablename__ = "card_identity"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    game: Mapped[Game] = mapped_column(
        Enum(Game, name="game", native_enum=False), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    set_code: Mapped[str | None] = mapped_column(String(64), index=True)
    set_name: Mapped[str | None] = mapped_column(String(255))
    number: Mapped[str | None] = mapped_column(String(32))
    rarity: Mapped[str | None] = mapped_column(String(64))
    variants: Mapped[dict[str, object] | None] = mapped_column(JSON, default=dict)
    attributes: Mapped[dict[str, object] | None] = mapped_column(JSON, default=dict)
    image_urls: Mapped[dict[str, object] | None] = mapped_column(JSON, default=dict)
    external_ids: Mapped[dict[str, object] | None] = mapped_column(JSON, default=dict)
    source: Mapped[str | None] = mapped_column(String(64), index=True)
    source_card_id: Mapped[str | None] = mapped_column(String(128), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    sale_events: Mapped[list["SaleEvent"]] = relationship(back_populates="card", lazy="raise")

    __table_args__ = (
        UniqueConstraint("game", "set_code", "number", name="uq_card_game_set_number"),
        UniqueConstraint("game", "source", "source_card_id", name="uq_card_game_source_id"),
    )


class SourceRun(Base):
    __tablename__ = "source_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[SourceRunStatus] = mapped_column(
        Enum(SourceRunStatus, name="source_run_status", native_enum=False),
        nullable=False,
    )
    inserted_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(String(1024))
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    dry_run: Mapped[bool] = mapped_column(default=False)


class SaleEvent(Base):
    __tablename__ = "sale_event"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    card_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("card_identity.id"), nullable=False, index=True
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    kind: Mapped[SaleKind] = mapped_column(
        Enum(SaleKind, name="sale_kind", native_enum=False), nullable=False
    )
    sold_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    price: Mapped[Decimal] = mapped_column(DECIMAL(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    price_usd: Mapped[Decimal | None] = mapped_column(DECIMAL(12, 2))
    grade_company: Mapped[str | None] = mapped_column(String(16))
    grade: Mapped[str | None] = mapped_column(String(16))
    condition: Mapped[str | None] = mapped_column(String(32))
    listing_url: Mapped[str | None] = mapped_column(String(512))
    raw_payload: Mapped[dict[str, object] | None] = mapped_column(JSON)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    card: Mapped[CardIdentity] = relationship(back_populates="sale_events")

    __table_args__ = (
        UniqueConstraint("source", "listing_url", "sold_at", name="uq_sale_dedup"),
        Index("ix_sale_card_soldat", "card_id", "sold_at"),
    )


class MarketplaceListing(Base):
    """Active marketplace listings ingested from official APIs (e.g. eBay Browse)."""

    __tablename__ = "marketplace_listings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_listing_id: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    price: Mapped[Decimal] = mapped_column(DECIMAL(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    condition: Mapped[str | None] = mapped_column(String(64))
    image_url: Mapped[str | None] = mapped_column(String(1024))
    item_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    seller_username: Mapped[str | None] = mapped_column(String(128))
    marketplace: Mapped[str] = mapped_column(String(32), nullable=False, default="EBAY_GB")
    listing_status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    affiliate_status: Mapped[str | None] = mapped_column(String(32))
    grade: Mapped[str | None] = mapped_column(String(32))
    raw_metadata: Mapped[dict[str, object] | None] = mapped_column(JSON)
    card_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("card_identity.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    __table_args__ = (
        UniqueConstraint("source", "source_listing_id", name="uq_marketplace_listing_source_id"),
    )


class CardPriceDaily(Base):
    __tablename__ = "card_price_daily"

    card_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("card_identity.id"), primary_key=True
    )
    day: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    grade_bucket: Mapped[str] = mapped_column(String(16), primary_key=True)  # 'raw' | 'PSA9' | ...
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False)
    mean_usd: Mapped[Decimal] = mapped_column(DECIMAL(12, 2), nullable=False)
    median_usd: Mapped[Decimal] = mapped_column(DECIMAL(12, 2), nullable=False)
    min_usd: Mapped[Decimal] = mapped_column(DECIMAL(12, 2), nullable=False)
    max_usd: Mapped[Decimal] = mapped_column(DECIMAL(12, 2), nullable=False)


class CardPopulation(Base):
    """Grading-company population report snapshot per (card, company, grade)."""

    __tablename__ = "card_population"

    card_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("card_identity.id"), primary_key=True
    )
    grade_company: Mapped[str] = mapped_column(String(16), primary_key=True)  # PSA | BGS | CGC
    grade: Mapped[str] = mapped_column(String(16), primary_key=True)  # '10', '9.5', ...
    pop_count: Mapped[int] = mapped_column(Integer, nullable=False)
    as_of: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class FxRate(Base):
    __tablename__ = "fx_rate"

    day: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    currency: Mapped[str] = mapped_column(String(3), primary_key=True)
    rate_to_usd: Mapped[Decimal] = mapped_column(DECIMAL(18, 8), nullable=False)


class UserTier(str, enum.Enum):
    free = "free"
    pro = "pro"


class UserRole(str, enum.Enum):
    user = "user"
    admin = "admin"
    admin_senior = "admin_senior"
    owner = "owner"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supabase_user_id: Mapped[str | None] = mapped_column(
        String(36), unique=True, nullable=True, index=True
    )
    email: Mapped[str | None] = mapped_column(String(255))
    tier: Mapped[UserTier] = mapped_column(
        Enum(UserTier, name="user_tier", native_enum=False), nullable=False, default=UserTier.free
    )
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", native_enum=False),
        nullable=False,
        default=UserRole.user,
        server_default="user",
    )
    account_seq: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    account_number: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
    comps_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=30, server_default="30"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    portfolio_items: Mapped[list["PortfolioItem"]] = relationship(
        back_populates="user", lazy="raise"
    )
    alerts: Mapped[list["PriceAlert"]] = relationship(back_populates="user", lazy="raise")


class PortfolioItem(Base):
    __tablename__ = "portfolio_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    card_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("card_identity.id"), nullable=False, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    cost_basis_usd: Mapped[Decimal | None] = mapped_column(DECIMAL(12, 2))
    notes: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="portfolio_items")
    card: Mapped[CardIdentity] = relationship(lazy="raise")

    __table_args__ = (UniqueConstraint("user_id", "card_id", name="uq_portfolio_user_card"),)


class WatchlistItem(Base):
    """Card a user watches without owning — Pro feature (Card Ladder parity)."""

    __tablename__ = "watchlist_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    card_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("card_identity.id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(lazy="raise")
    card: Mapped[CardIdentity] = relationship(lazy="raise")

    __table_args__ = (UniqueConstraint("user_id", "card_id", name="uq_watchlist_user_card"),)


class SavedSearch(Base):
    """Saved ladder search — filter/sort params snapshot per user."""

    __tablename__ = "saved_searches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    params: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(lazy="raise")

    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_saved_search_user_name"),)


class AlertDirection(str, enum.Enum):
    below = "below"
    above = "above"


class PriceAlert(Base):
    __tablename__ = "price_alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    card_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("card_identity.id"), nullable=False, index=True
    )
    direction: Mapped[AlertDirection] = mapped_column(
        Enum(AlertDirection, name="alert_direction", native_enum=False), nullable=False
    )
    threshold_usd: Mapped[Decimal] = mapped_column(DECIMAL(12, 2), nullable=False)
    grade_filter: Mapped[str | None] = mapped_column(String(16))
    active: Mapped[bool] = mapped_column(nullable=False, default=True)
    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="alerts")
    card: Mapped[CardIdentity] = relationship(lazy="raise")
