import { describe, expect, it } from "vitest";
import { cardDetailHref, cardSlugFromCard } from "./card-slug";
import type { CardOut } from "@tcgscan/sdk-ts";

const ONE_PIECE_CARD: CardOut = {
  id: "00000000-0000-4000-8000-000000000001",
  slug: "one_piece-st-08-st08-004",
  game: "one_piece",
  name: "Starter Card",
  set_code: "ST-08",
  set_name: "Starter Deck 08",
  number: "ST08-004",
  card_number: "ST08-004",
  source: "optcgapi",
  price_status: "pending",
};

describe("cardSlugFromCard", () => {
  it("uses API slug when present", () => {
    expect(cardSlugFromCard(ONE_PIECE_CARD)).toBe("one_piece-st-08-st08-004");
  });

  it("builds slug from game, set, and number when slug missing", () => {
    const card = { ...ONE_PIECE_CARD, slug: "" };
    expect(cardSlugFromCard(card)).toBe("one_piece-st-08-st08-004");
  });

  it("links to canonical /card route", () => {
    expect(cardDetailHref(ONE_PIECE_CARD)).toBe("/card/one_piece-st-08-st08-004");
  });
});
