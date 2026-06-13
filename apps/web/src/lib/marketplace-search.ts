export type MarketplaceCard = {
  name: string;
  game: string;
  set_name?: string | null;
  set_code?: string | null;
  number?: string | null;
};

const CARDMARKET_GAMES: Record<string, string> = {
  pokemon: "Pokemon",
  mtg: "Magic",
  yugioh: "YuGiOh",
  lorcana: "Lorcana",
  one_piece: "OnePiece",
  sports: "Sports",
};

const TCGPLAYER_GAMES: Record<string, string> = {
  pokemon: "pokemon",
  mtg: "magic",
  yugioh: "yugioh",
  lorcana: "disney-lorcana",
  one_piece: "one-piece-card-game",
  sports: "sports",
};

export function cardSearchQuery(card: MarketplaceCard): string {
  const parts = [card.name];
  if (card.set_name) parts.push(card.set_name);
  else if (card.set_code) parts.push(card.set_code);
  if (card.number) parts.push(card.number);
  return parts.filter(Boolean).join(" ").trim();
}

export function ebaySearchUrl(query: string, marketplace: "EBAY_GB" | "EBAY_US" = "EBAY_GB"): string {
  const host = marketplace === "EBAY_GB" ? "www.ebay.co.uk" : "www.ebay.com";
  return `https://${host}/sch/i.html?_nkw=${encodeURIComponent(query)}`;
}

export function tcgplayerSearchUrl(card: MarketplaceCard): string {
  const gameSlug = TCGPLAYER_GAMES[card.game.toLowerCase()] ?? "pokemon";
  const query = cardSearchQuery(card);
  return `https://www.tcgplayer.com/search/${gameSlug}/product?q=${encodeURIComponent(query)}`;
}

export function cardmarketSearchUrl(card: MarketplaceCard): string {
  const gameSlug = CARDMARKET_GAMES[card.game.toLowerCase()] ?? "Pokemon";
  const query = cardSearchQuery(card);
  return (
    `https://www.cardmarket.com/en/${gameSlug}/Products/Singles/search` +
    `?searchString=${encodeURIComponent(query)}`
  );
}

export function marketplaceSearchUrls(card: MarketplaceCard): Record<"ebay" | "tcgplayer" | "cardmarket", string> {
  const query = cardSearchQuery(card);
  return {
    ebay: ebaySearchUrl(query),
    tcgplayer: tcgplayerSearchUrl(card),
    cardmarket: cardmarketSearchUrl(card),
  };
}
