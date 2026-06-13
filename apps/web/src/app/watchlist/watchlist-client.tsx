"use client";

import Image from "next/image";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import type { WatchlistItemOut } from "@tcgscan/sdk-ts";
import { getWatchlist, removeFromWatchlist } from "@tcgscan/sdk-ts";
import { useCurrency } from "@/lib/currency";

function thumb(item: WatchlistItemOut): string | null {
  const urls = item.card.image_urls;
  if (!urls) return null;
  const src = urls.small ?? urls.front ?? urls.hires;
  return typeof src === "string" ? src : null;
}

export function WatchlistClient() {
  const [items, setItems] = useState<WatchlistItemOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { fmt: fmtMoney } = useCurrency();

  useEffect(() => {
    getWatchlist()
      .then(setItems)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load watchlist"))
      .finally(() => setLoading(false));
  }, []);

  const onRemove = useCallback(async (id: string) => {
    setItems((prev) => prev.filter((i) => i.id !== id));
    try {
      await removeFromWatchlist(id);
    } catch {
      // best effort — list refreshes on next mount
    }
  }, []);

  if (loading) return <p className="text-sm text-zinc-500">Loading…</p>;
  if (error) return <p className="text-sm text-red-600">{error}</p>;

  return (
    <ul className="divide-y divide-zinc-100 overflow-hidden rounded-xl border border-zinc-200 bg-white">
      {items.map((item) => {
        const img = thumb(item);
        return (
          <li key={item.id} className="flex items-center gap-3 px-4 py-3">
            {img ? (
              <Image
                src={img}
                alt={item.card.name}
                width={40}
                height={56}
                className="shrink-0 rounded border border-zinc-200 object-cover"
              />
            ) : (
              <div className="h-14 w-10 shrink-0 rounded border border-zinc-200 bg-zinc-100" />
            )}
            <div className="min-w-0 flex-1">
              <Link
                href={`/card/${item.card.slug}`}
                className="block truncate font-medium hover:text-blue-700"
              >
                {item.card.name}
                {item.card.number ? (
                  <span className="text-zinc-400"> #{item.card.number}</span>
                ) : null}
              </Link>
              <p className="truncate text-xs text-zinc-500">
                {item.card.set_name ?? item.card.set_code} · {item.card.game}
              </p>
            </div>
            <div className="shrink-0 text-right">
              <p className="text-[11px] uppercase tracking-wide text-zinc-400">30d median</p>
              <p className="font-semibold">{fmtMoney(item.median_usd_30d)}</p>
            </div>
            <button
              type="button"
              aria-label={`Remove ${item.card.name} from watchlist`}
              onClick={() => void onRemove(item.id)}
              className="shrink-0 p-2 text-zinc-400 hover:text-red-600"
            >
              ×
            </button>
          </li>
        );
      })}
      {items.length === 0 && (
        <li className="px-4 py-10 text-center text-sm text-zinc-500">
          Your watchlist is empty. Browse the{" "}
          <Link href="/ladder" className="text-blue-700 hover:underline">
            Ladder
          </Link>{" "}
          and tap Watch on any card.
        </li>
      )}
    </ul>
  );
}
