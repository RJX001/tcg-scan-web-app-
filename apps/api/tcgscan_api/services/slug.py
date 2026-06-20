"""URL slug helpers for SEO-friendly card pages."""

from __future__ import annotations

from tcgscan_api.db.models import CardIdentity, Game

# Longest game prefix first so `dragon_ball_fusion_world` wins over `dragon`.
_GAME_VALUES: tuple[str, ...] = tuple(
    sorted((g.value for g in Game), key=len, reverse=True)
)


def _game_str(game: Game | str) -> str:
    return game.value if isinstance(game, Game) else str(game)


def _slug_part(value: str) -> str:
    return value.lower().replace("/", "-")


def match_game_prefix(slug: str) -> Game | None:
    slug_lower = slug.lower().strip()
    for game_value in _GAME_VALUES:
        if slug_lower == game_value:
            return Game(game_value)
        if slug_lower.startswith(f"{game_value}-"):
            return Game(game_value)
    return None


def card_slug(game: Game | str, set_code: str | None, number: str | None) -> str:
    g = _game_str(game)
    sc = _slug_part(set_code or "unknown")
    num = _slug_part(number or "0")
    return f"{g}-{sc}-{num}"


def card_slug_from_source(game: Game | str, source: str, source_card_id: str) -> str:
    g = _game_str(game)
    return f"{g}-{source}-{_slug_part(source_card_id)}"


def card_slug_from_identity(card: CardIdentity) -> str:
    if card.set_code and card.number:
        return card_slug(card.game, card.set_code, card.number)
    if card.source and card.source_card_id:
        return card_slug_from_source(card.game, card.source, card.source_card_id)
    return card_slug(card.game, card.set_code, card.number)


def parse_card_slug(slug: str) -> tuple[str, str, str]:
    game = match_game_prefix(slug)
    if game is None:
        msg = f"invalid card slug: {slug}"
        raise ValueError(msg)
    slug_lower = slug.lower().strip()
    if slug_lower == game.value:
        msg = f"invalid card slug: {slug}"
        raise ValueError(msg)
    remainder = slug_lower[len(game.value) + 1 :]
    parts = remainder.split("-")
    if not parts:
        msg = f"invalid card slug: {slug}"
        raise ValueError(msg)
    set_code = parts[0]
    number = "/".join(parts[1:]) if len(parts) > 1 else "0"
    return game.value, set_code, number


def slug_remainder(slug: str) -> str | None:
    game = match_game_prefix(slug)
    if game is None:
        return None
    slug_lower = slug.lower().strip()
    if slug_lower == game.value:
        return None
    return slug_lower[len(game.value) + 1 :]
