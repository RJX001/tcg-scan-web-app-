import { describe, expect, it } from "vitest";
import { cardmarketSearchUrl, cardSearchQuery, ebaySearchUrl, tcgplayerSearchUrl } from "./marketplace-search";

describe("marketplace-search", () => {
  const card = {
    name: "Charizard",
    game: "pokemon",
    set_name: "Base Set",
    number: "4/102",
  };

  it("builds a descriptive search query", () => {
    expect(cardSearchQuery(card)).toBe("Charizard Base Set 4/102");
  });

  it("builds marketplace URLs", () => {
    const query = cardSearchQuery(card);
    expect(ebaySearchUrl(query)).toContain("ebay.co.uk");
    expect(ebaySearchUrl(query)).toContain("Charizard");
    expect(tcgplayerSearchUrl(card)).toContain("tcgplayer.com/search/pokemon/");
    expect(cardmarketSearchUrl(card)).toContain("cardmarket.com/en/Pokemon/");
  });
});
