"""Build marketplace search URLs for a catalog card."""

from __future__ import annotations

from urllib.parse import quote_plus

from tcgscan_api.config import get_settings
from tcgscan_api.services.cards import CardOut

_CARDMARKET_GAMES: dict[str, str] = {
    "pokemon": "Pokemon",
    "mtg": "Magic",
    "yugioh": "YuGiOh",
    "lorcana": "Lorcana",
    "one_piece": "OnePiece",
    "sports": "Sports",
}

_TCGPLAYER_GAMES: dict[str, str] = {
    "pokemon": "pokemon",
    "mtg": "magic",
    "yugioh": "yugioh",
    "lorcana": "disney-lorcana",
    "one_piece": "one-piece-card-game",
    "sports": "sports",
}


def card_search_query(card: CardOut) -> str:
    parts = [card.name]
    if card.set_name:
        parts.append(card.set_name)
    elif card.set_code:
        parts.append(card.set_code)
    if card.number:
        parts.append(card.number)
    return " ".join(p for p in parts if p).strip()


def ebay_search_url(query: str) -> str:
    marketplace = get_settings().ebay_marketplace_id.upper()
    host = "www.ebay.co.uk" if marketplace == "EBAY_GB" else "www.ebay.com"
    return f"https://{host}/sch/i.html?_nkw={quote_plus(query)}"


def tcgplayer_search_url(card: CardOut) -> str:
    game_slug = _TCGPLAYER_GAMES.get(card.game.lower(), "pokemon")
    query = card_search_query(card)
    return f"https://www.tcgplayer.com/search/{game_slug}/product?q={quote_plus(query)}"


def cardmarket_search_url(card: CardOut) -> str:
    game_slug = _CARDMARKET_GAMES.get(card.game.lower(), "Pokemon")
    query = card_search_query(card)
    return (
        f"https://www.cardmarket.com/en/{game_slug}/Products/Singles/search"
        f"?searchString={quote_plus(query)}"
    )


def marketplace_search_urls(card: CardOut) -> dict[str, str]:
    query = card_search_query(card)
    return {
        "ebay": ebay_search_url(query),
        "tcgplayer": tcgplayer_search_url(card),
        "cardmarket": cardmarket_search_url(card),
    }
