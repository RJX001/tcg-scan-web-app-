/** Supported TCGs in the scan + search flows (matches `Game` enum slugs in the API). */
export const SCAN_GAMES = [
  { value: "pokemon", label: "Pokemon" },
  { value: "mtg", label: "Magic" },
  { value: "yugioh", label: "Yu-Gi-Oh!" },
  { value: "lorcana", label: "Lorcana" },
  { value: "one_piece", label: "One Piece" },
] as const;

export type ScanGameSlug = (typeof SCAN_GAMES)[number]["value"];

/** Dev/demo catalog cards — one flagship per game after `pnpm db:demo`. */
export const DEMO_CARDS: { slug: string; label: string; game: ScanGameSlug }[] = [
  { slug: "pokemon-base1-4-102", label: "Charizard", game: "pokemon" },
  { slug: "pokemon-base1-58-102", label: "Pikachu", game: "pokemon" },
  { slug: "mtg-m10-146", label: "Lightning Bolt", game: "mtg" },
  { slug: "yugioh-sdy-006", label: "Dark Magician", game: "yugioh" },
  { slug: "lorcana-tfc-001", label: "Mickey Mouse", game: "lorcana" },
  { slug: "one_piece-op01-001", label: "Luffy (OP01)", game: "one_piece" },
];
