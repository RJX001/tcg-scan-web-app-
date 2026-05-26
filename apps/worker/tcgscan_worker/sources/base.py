from __future__ import annotations

import abc
import uuid
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

import structlog

from tcgscan_worker.http import ResilientClient

log = structlog.get_logger()


@dataclass
class SaleRecord:
    """Normalised cross-marketplace sale/listing."""

    source: str
    kind: str  # 'sold' | 'listing'
    sold_at: datetime
    price: Decimal
    currency: str
    price_usd: Decimal | None
    grade_company: str | None
    grade: str | None
    condition: str | None
    listing_url: str | None
    raw_payload: dict[str, Any]
    card_id: uuid.UUID | None = None  # filled by resolver

    def to_row(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "kind": self.kind,
            "sold_at": self.sold_at,
            "price": self.price,
            "currency": self.currency,
            "price_usd": self.price_usd,
            "grade_company": self.grade_company,
            "grade": self.grade,
            "condition": self.condition,
            "listing_url": self.listing_url,
            "raw_payload": self.raw_payload,
            "card_id": self.card_id,
        }


class PriceSource(abc.ABC):
    """Pluggable price/comp source. Use `iter_records` for batches."""

    source_id: str = ""

    def __init__(self, client: ResilientClient | None = None) -> None:
        self._client = client

    @property
    def client(self) -> ResilientClient:
        if self._client is None:
            self._client = self._build_client()
        return self._client

    @abc.abstractmethod
    def _build_client(self) -> ResilientClient: ...

    @abc.abstractmethod
    def iter_records(self, *, query: str, limit: int = 100) -> AsyncIterator[SaleRecord]: ...


REGISTRY: dict[str, type[PriceSource]] = {}


def register(slug: str) -> Callable[[type[PriceSource]], type[PriceSource]]:
    def deco(cls: type[PriceSource]) -> type[PriceSource]:
        cls.source_id = slug
        REGISTRY[slug] = cls
        log.debug("source.register", source=slug)
        return cls

    return deco
