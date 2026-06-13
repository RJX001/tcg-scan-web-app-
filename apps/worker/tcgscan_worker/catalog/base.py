from __future__ import annotations

import abc
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from typing import Any

import structlog

from tcgscan_worker.http import ResilientClient

log = structlog.get_logger()


@dataclass
class CatalogCard:
    game: str
    name: str
    set_code: str | None
    set_name: str | None
    number: str | None
    rarity: str | None
    image_urls: dict[str, str]
    external_ids: dict[str, str]
    attributes: dict[str, Any]
    variants: dict[str, Any]


class CatalogIngester(abc.ABC):
    """Async, idempotent catalog ingester for one game."""

    game: str = ""

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
    def iter_cards(self, *, limit: int | None = None) -> AsyncIterator[CatalogCard]: ...

    def to_row(self, card: CatalogCard) -> dict[str, Any]:
        return {
            "game": card.game,
            "name": card.name,
            "set_code": card.set_code,
            "set_name": card.set_name,
            "number": card.number,
            "rarity": card.rarity,
            "image_urls": card.image_urls,
            "external_ids": card.external_ids,
            "attributes": card.attributes,
            "variants": card.variants,
        }


REGISTRY: dict[str, type[CatalogIngester]] = {}


def register(slug: str) -> Callable[[type[CatalogIngester]], type[CatalogIngester]]:
    def deco(cls: type[CatalogIngester]) -> type[CatalogIngester]:
        cls.game = slug
        REGISTRY[slug] = cls
        log.debug("catalog.register", game=slug)
        return cls

    return deco
