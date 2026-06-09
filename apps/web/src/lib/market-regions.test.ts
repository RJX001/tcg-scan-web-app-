import { describe, expect, it } from "vitest";
import { inferMarketRegion, matchesMarketRegionFilter } from "./market-regions";

describe("market-regions", () => {
  it("classifies US marketplace comps", () => {
    expect(
      inferMarketRegion({
        source: "tcgplayer",
        currency: "USD",
        listing_url: "https://www.tcgplayer.com/product/123",
      }),
    ).toBe("us");
    expect(
      inferMarketRegion({
        source: "ebay",
        currency: "USD",
        listing_url: "https://www.ebay.com/itm/123",
      }),
    ).toBe("us");
  });

  it("classifies UK and EU marketplace comps", () => {
    expect(
      inferMarketRegion({
        source: "ebay",
        currency: "GBP",
        listing_url: "https://www.ebay.co.uk/itm/123",
      }),
    ).toBe("uk");
    expect(
      inferMarketRegion({
        source: "cardmarket",
        currency: "EUR",
        listing_url: "https://www.cardmarket.com/en/Pokemon/123",
      }),
    ).toBe("eu");
  });

  it("filters by selected market region", () => {
    const ukSale = {
      source: "ebay",
      currency: "GBP",
      listing_url: "https://www.ebay.co.uk/itm/123",
      market_region: "uk",
    };
    expect(matchesMarketRegionFilter(ukSale, "uk")).toBe(true);
    expect(matchesMarketRegionFilter(ukSale, "us")).toBe(false);
    expect(matchesMarketRegionFilter(ukSale, "all")).toBe(true);
  });
});
