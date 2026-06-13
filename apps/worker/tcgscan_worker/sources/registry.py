"""Side-effect imports populate REGISTRY for runtime use."""

from tcgscan_worker.sources import (  # noqa: F401
    cardmarket,
    ebay_active,
    ebay_sold,
    tcgplayer,
)
from tcgscan_worker.sources.base import REGISTRY, PriceSource

__all__ = ["REGISTRY", "get_source"]


def get_source(source_id: str) -> PriceSource:
    cls = REGISTRY.get(source_id)
    if cls is None:
        msg = f"unknown price source: {source_id}"
        raise KeyError(msg)
    return cls()
