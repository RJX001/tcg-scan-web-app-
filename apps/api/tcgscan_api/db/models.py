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
    lorcana = "lorcana"
    star_wars_unlimited = "star_wars_unlimited"
    flesh_and_blood = "flesh_and_blood"
    digimon = "digimon"
    sports_baseball = "sports_baseball"
    sports_basketball = "sports_basketball"
    sports_football = "sports_football"
    sports_soccer = "sports_soccer"
    other = "other"


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
    )


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


class FxRate(Base):
    __tablename__ = "fx_rate"

    day: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    currency: Mapped[str] = mapped_column(String(3), primary_key=True)
    rate_to_usd: Mapped[Decimal] = mapped_column(DECIMAL(18, 8), nullable=False)


class UserTier(str, enum.Enum):
    free = "free"
    pro = "pro"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clerk_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(255))
    tier: Mapped[UserTier] = mapped_column(
        Enum(UserTier, name="user_tier", native_enum=False), nullable=False, default=UserTier.free
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    portfolio_items: Mapped[list["PortfolioItem"]] = relationship(back_populates="user", lazy="raise")
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
