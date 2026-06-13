"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import type { MarketMoverOut } from "@tcgscan/sdk-ts";
import { getMarketMovers } from "@tcgscan/sdk-ts";

const GAMES = [
  { value: "", label: "All games" },
  { value: "pokemon", label: "Pokemon" },
  { value: "mtg", label: "Magic" },
  { value: "yugioh", label: "Yu-Gi-Oh!" },
  { value: "lorcana", label: "Lorcana" },
  { value: "one_piece", label: "One Piece" },
];

const SORTS = [
  { value: "recent", label: "Recently sold" },
  { value: "alpha", label: "Alphabetical" },
  { value: "number", label: "Number" },
] as const;

type ShowSort = (typeof SORTS)[number]["value"];

function thumb(m: MarketMoverOut): string | null {
  const urls = m.card.image_urls;
  if (!urls) return null;
  const src = urls.front ?? urls.hires ?? urls.small;
  return typeof src === "string" ? src : null;
}

function numKey(n: string | null | undefined): number {
  const match = /\d+/.exec(n ?? "");
  return match ? Number(match[0]) : Number.MAX_SAFE_INTEGER;
}

export function ShowcaseClient() {
  const [game, setGame] = useState("");
  const [sort, setSort] = useState<ShowSort>("recent");
  const [rows, setRows] = useState<MarketMoverOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getMarketMovers({ game: game || undefined, sort: "recent", limit: 60, days: 365 })
      .then((out) => {
        if (!cancelled) setRows(out);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load showcase");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [game]);

  const sorted = useMemo(() => {
    const copy = [...rows];
    if (sort === "alpha") copy.sort((a, b) => a.card.name.localeCompare(b.card.name));
    if (sort === "number") copy.sort((a, b) => numKey(a.card.number) - numKey(b.card.number));
    return copy;
  }, [rows, sort]);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap gap-2">
        <select
          value={game}
          onChange={(e) => setGame(e.target.value)}
          className="rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm"
        >
          {GAMES.map((g) => (
            <option key={g.value} value={g.value}>
              {g.label}
            </option>
          ))}
        </select>
        {SORTS.map((s) => (
          <button
            key={s.value}
            type="button"
            onClick={() => setSort(s.value)}
            className={`rounded-full border px-3 py-1 text-xs font-medium ${
              sort === s.value
                ? "border-blue-700 bg-blue-700 text-white"
                : "border-zinc-300 bg-white text-zinc-600 hover:border-zinc-400"
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        {sorted.map((m) => {
          const img = thumb(m);
          return (
            <li key={m.card.id}>
              <Link
                href={`/card/${m.card.slug}`}
                className="group block overflow-hidden rounded-xl border border-zinc-200 bg-white"
              >
                <div className="relative aspect-[3/4] bg-zinc-100">
                  {img ? (
                    <Image
                      src={img}
                      alt={m.card.name}
                      fill
                      sizes="(max-width: 640px) 50vw, 25vw"
                      className="object-contain p-2 transition-transform group-hover:scale-105"
                    />
                  ) : (
                    <div className="flex h-full items-center justify-center text-xs text-zinc-400">
                      No image
                    </div>
                  )}
                </div>
                <div className="px-3 py-2">
                  <p className="truncate text-sm font-medium">{m.card.name}</p>
                  <p className="truncate text-xs text-zinc-500">
                    {m.card.set_name ?? m.card.set_code}
                    {m.card.number ? ` · #${m.card.number}` : ""}
                  </p>
                </div>
              </Link>
            </li>
          );
        })}
      </ul>
      {loading && <p className="text-center text-sm text-zinc-500">Loading…</p>}
      {!loading && sorted.length === 0 && !error && (
        <p className="text-center text-sm text-zinc-500">
          Nothing to show yet — run <code className="rounded bg-zinc-100 px-1">pnpm db:seed</code>.
        </p>
      )}
    </div>
  );
}
