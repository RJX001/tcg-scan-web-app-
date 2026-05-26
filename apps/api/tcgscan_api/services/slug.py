"""URL slug helpers for SEO-friendly card pages."""

from __future__ import annotations

from tcgscan_api.db.models import CardIdentity, Game


def card_slug(game: Game | str, set_code: str | None, number: str | None) -> str:
    g = game.value if isinstance(game, Game) else str(game)
    sc = (set_code or "unknown").lower()
    num = (number or "0").replace("/", "-")
    return f"{g}-{sc}-{num}".lower()


def card_slug_from_identity(card: CardIdentity) -> str:
    return card_slug(card.game, card.set_code, card.number)


def parse_card_slug(slug: str) -> tuple[str, str, str]:
    parts = slug.lower().split("-")
    if len(parts) < 3:
        msg = f"invalid card slug: {slug}"
        raise ValueError(msg)
    game, set_code = parts[0], parts[1]
    number = "/".join(parts[2:]) if len(parts) > 3 else parts[2]
    return game, set_code, number
