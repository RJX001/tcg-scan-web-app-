import type { CardOut } from "@tcgscan/sdk-ts";

function slugPart(value: string): string {
  return value.toLowerCase().replace(/\//g, "-");
}

/** Client-side fallback when API omits slug (should match backend card_slug helpers). */
export function cardSlugFromCard(card: CardOut): string {
  if (card.slug) return card.slug;
  const game = card.game.toLowerCase();
  if (card.set_code && (card.card_number || card.number)) {
    const setCode = slugPart(card.set_code);
    const number = slugPart(card.card_number ?? card.number ?? "0");
    return `${game}-${setCode}-${number}`;
  }
  if (card.source && card.metadata && typeof card.metadata === "object") {
    const sourceCardId = (card.metadata as Record<string, unknown>).source_card_id;
    if (typeof sourceCardId === "string" && sourceCardId) {
      return `${game}-${card.source}-${slugPart(sourceCardId)}`;
    }
  }
  return `${game}-unknown-0`;
}

export function cardDetailHref(card: CardOut): string {
  return `/card/${cardSlugFromCard(card)}`;
}
