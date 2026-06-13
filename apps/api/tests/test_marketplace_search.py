from tcgscan_api.services.cards import CardOut
from tcgscan_api.services.marketplace_search import (
    card_search_query,
    cardmarket_search_url,
    ebay_search_url,
    tcgplayer_search_url,
)


def test_card_search_query_includes_set_and_number() -> None:
    card = CardOut(
        id="1",
        slug="pokemon-base1-4-102",
        game="pokemon",
        name="Charizard",
        set_name="Base Set",
        number="4/102",
    )
    assert card_search_query(card) == "Charizard Base Set 4/102"


def test_marketplace_search_urls() -> None:
    card = CardOut(
        id="1",
        slug="pokemon-base1-4-102",
        game="pokemon",
        name="Charizard",
        set_name="Base Set",
        number="4/102",
    )
    ebay = ebay_search_url(card_search_query(card))
    assert "ebay" in ebay
    assert "Charizard" in ebay
    assert tcgplayer_search_url(card).startswith("https://www.tcgplayer.com/search/pokemon/")
    assert "www.cardmarket.com/en/Pokemon/" in cardmarket_search_url(card)
