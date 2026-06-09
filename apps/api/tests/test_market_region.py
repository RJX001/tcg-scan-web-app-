from tcgscan_api.services.market_region import infer_market_region


def test_infer_us_region() -> None:
    assert (
        infer_market_region(
            source="tcgplayer",
            currency="USD",
            listing_url="https://www.tcgplayer.com/product/1",
        )
        == "us"
    )
    assert (
        infer_market_region(
            source="ebay",
            currency="USD",
            listing_url="https://www.ebay.com/itm/1",
        )
        == "us"
    )


def test_infer_uk_and_eu_regions() -> None:
    assert (
        infer_market_region(
            source="ebay",
            currency="GBP",
            listing_url="https://www.ebay.co.uk/itm/1",
        )
        == "uk"
    )
    assert (
        infer_market_region(
            source="cardmarket",
            currency="EUR",
            listing_url="https://www.cardmarket.com/en/Pokemon/1",
        )
        == "eu"
    )
