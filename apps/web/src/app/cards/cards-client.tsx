"use client";

import { Button } from "@tcgscan/ui";
import type { CardOut } from "@tcgscan/sdk-ts";
import { searchCatalog } from "@tcgscan/sdk-ts";
import Image from "next/image";
import Link from "next/link";
import { useCallback, useState } from "react";

const GAMES = [
  { value: "", label: "All games" },
  { value: "pokemon", label: "Pokémon" },
  { value: "mtg", label: "Magic: The Gathering" },
  { value: "yugioh", label: "Yu-Gi-Oh!" },
  { value: "one_piece", label: "One Piece" },
  { value: "dragon_ball_fusion_world", label: "Dragon Ball Fusion World" },
  { value: "dragon_ball_masters", label: "Dragon Ball Masters" },
  { value: "lorcana", label: "Lorcana" },
];

function cardImage(card: CardOut): string | null {
  if (card.image_url) return card.image_url;
  const urls = card.image_urls;
  if (!urls) return null;
  const src = urls.large ?? urls.front ?? urls.small ?? urls.hires;
  return typeof src === "string" ? src : null;
}

function PriceLabel({ card }: { card: CardOut }) {
  if (card.price_status === "available" && card.current_value != null) {
    return <span className="text-sm font-semibold text-zinc-900">${card.current_value.toFixed(2)}</span>;
  }
  return <span className="text-xs text-zinc-500">Price pending</span>;
}

export function CardsClient() {
  const [q, setQ] = useState("");
  const [game, setGame] = useState("");
  const [results, setResults] = useState<CardOut[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  const onSearch = useCallback(async () => {
    if (!q.trim() && !game) return;
    setLoading(true);
    setError(null);
    setSearched(true);
    try {
      const out = await searchCatalog({
        q: q.trim() || undefined,
        game: game || undefined,
        limit: 48,
      });
      setResults(out);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search failed");
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, [q, game]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row">
        <input
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && void onSearch()}
          placeholder="Search by name, set, or number…"
          className="flex-1 rounded-lg border border-zinc-300 px-3 py-2 text-sm"
        />
        <select
          value={game}
          onChange={(e) => setGame(e.target.value)}
          className="rounded-lg border border-zinc-300 px-3 py-2 text-sm sm:w-52"
        >
          {GAMES.map((g) => (
            <option key={g.value || "all"} value={g.value}>
              {g.label}
            </option>
          ))}
        </select>
        <Button onClick={() => void onSearch()} disabled={loading || (!q.trim() && !game)}>
          {loading ? "Searching…" : "Search"}
        </Button>
      </div>

      <p className="text-xs text-zinc-500">
        Catalogue metadata only. Live marketplace pricing and listings are pending eBay/Cardmarket
        approval.
      </p>

      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      {searched && !loading && results.length === 0 && !error ? (
        <p className="rounded-lg border border-dashed border-zinc-300 px-4 py-10 text-center text-sm text-zinc-500">
          No cards found. Try a different search or ask an admin to ingest catalogue samples from{" "}
          <Link href="/admin/sources" className="text-blue-700 underline">
            Admin → Sources
          </Link>
          .
        </p>
      ) : null}

      <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {results.map((card) => {
          const img = cardImage(card);
          return (
            <li key={card.id}>
              <Link
                href={`/card/${card.slug}`}
                className="flex h-full flex-col overflow-hidden rounded-xl border border-zinc-200 bg-white hover:border-zinc-300 hover:shadow-sm"
              >
                <div className="relative aspect-[3/4] bg-zinc-50">
                  {img ? (
                    <Image src={img} alt={card.name} fill className="object-contain p-2" sizes="200px" />
                  ) : (
                    <div className="flex h-full items-center justify-center text-xs text-zinc-400">
                      No image
                    </div>
                  )}
                </div>
                <div className="flex flex-1 flex-col gap-1 p-3">
                  <p className="line-clamp-2 font-medium leading-snug">{card.name}</p>
                  <p className="text-xs text-zinc-500">
                    {card.set_name ?? card.set_code}
                    {card.card_number ? ` · ${card.card_number}` : ""}
                  </p>
                  {card.rarity ? (
                    <p className="text-xs uppercase tracking-wide text-zinc-400">{card.rarity}</p>
                  ) : null}
                  <div className="mt-auto pt-2">
                    <PriceLabel card={card} />
                  </div>
                </div>
              </Link>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
