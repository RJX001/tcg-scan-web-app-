"use client";

import { Money } from "@/lib/currency";
import type { SourcePrices } from "@tcgscan/sdk-ts";
import { getAccount, getSourcePrices } from "@tcgscan/sdk-ts";
import { ExternalLink } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

type Props = {
  cardId: string;
  initial?: SourcePrices;
  /** Daylight accent styling for card detail page. */
  tone?: "default" | "daylight";
};

const FALLBACK_LABELS: Record<string, string> = {
  ebay: "eBay",
  tcgplayer: "TCGPlayer",
  cardmarket: "Cardmarket",
};

export function MarketplacePrices({ cardId, initial, tone = "default" }: Props) {
  const daylight = tone === "daylight";
  const [prices, setPrices] = useState<SourcePrices | undefined>(initial);
  const [days, setDays] = useState(initial?.days ?? 30);
  const [loading, setLoading] = useState(!initial);
  const [isPro, setIsPro] = useState(false);

  const load = useCallback(
    async (windowDays?: number) => {
      setLoading(true);
      try {
        const [account, sourcePrices] = await Promise.all([
          getAccount().catch(() => null),
          getSourcePrices(cardId, windowDays),
        ]);
        if (account) {
          setIsPro(account.tier === "pro");
        }
        setDays(sourcePrices.days ?? windowDays ?? 30);
        setPrices(sourcePrices);
      } finally {
        setLoading(false);
      }
    },
    [cardId],
  );

  useEffect(() => {
    void load();
  }, [load]);

  const tiles =
    prices?.marketplaces?.length === 3
      ? prices.marketplaces
      : [
          {
            source: "ebay",
            label: "eBay",
            avg_usd: prices?.ebay_median_usd,
            sample_count: 0,
            search_url: "",
          },
          {
            source: "tcgplayer",
            label: "TCGPlayer",
            avg_usd: prices?.tcgplayer_median_usd,
            sample_count: 0,
            search_url: "",
          },
          {
            source: "cardmarket",
            label: "Cardmarket",
            avg_usd: prices?.cardmarket_median_usd,
            sample_count: 0,
            search_url: "",
          },
        ];

  const muted = daylight ? "text-[#84878F]" : "text-zinc-500";
  const price = daylight ? "text-[#17181C]" : "text-zinc-900";
  const link = daylight ? "text-[#B6862E]" : "text-blue-600";
  const tileClass = daylight
    ? "rounded-[11px] border border-[#E4E1D8] bg-[#F7F6F2] p-3 transition-colors hover:border-[#B6862E]/60"
    : "rounded-lg border border-zinc-200 bg-white p-3 transition-colors hover:border-blue-300 hover:bg-blue-50/40";

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className={`text-xs uppercase tracking-wide ${muted}`}>
          Marketplace averages · last {days} days
        </p>
        {isPro ? (
          <label className={`flex items-center gap-2 text-xs ${daylight ? "text-[#5B5F68]" : "text-zinc-600"}`}>
            Window
            <select
              value={days}
              onChange={(e) => void load(Number(e.target.value))}
              className={
                daylight
                  ? "rounded border border-[#E4E1D8] bg-white px-2 py-1 text-xs"
                  : "rounded border border-zinc-300 px-2 py-1 text-xs"
              }
              disabled={loading}
            >
              <option value={7}>7 days</option>
              <option value={30}>30 days</option>
              <option value={90}>90 days</option>
              <option value={180}>180 days</option>
            </select>
          </label>
        ) : (
          <Link href="/account" className={`text-xs hover:underline ${link}`}>
            Pro: custom window in Account →
          </Link>
        )}
      </div>

      <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
        {tiles.map((tile) => {
          const label = tile.label || FALLBACK_LABELS[tile.source] || tile.source;
          const href = tile.search_url;
          const content = (
            <>
              <div className="flex items-center justify-between gap-2">
                <p className={`text-xs uppercase tracking-wide ${muted}`}>{label}</p>
                {href ? (
                  <ExternalLink
                    className={`h-3.5 w-3.5 ${daylight ? "text-[#84878F]" : "text-zinc-400"}`}
                    aria-hidden
                  />
                ) : null}
              </div>
              <p className={`mt-1 text-lg font-semibold ${price}`}>
                {loading ? "…" : <Money usd={tile.avg_usd} />}
              </p>
              {tile.sample_count > 0 ? (
                <p className={`mt-1 text-xs ${muted}`}>
                  {tile.sample_count} sale{tile.sample_count === 1 ? "" : "s"}
                </p>
              ) : !loading && tile.avg_usd == null ? (
                <p className={`mt-1 text-xs ${daylight ? "text-[#84878F]" : "text-zinc-400"}`}>
                  No comps yet
                </p>
              ) : null}
              {href ? (
                <p className={`mt-2 text-xs font-medium group-hover:underline ${link}`}>
                  Search on {label} →
                </p>
              ) : null}
            </>
          );

          if (!href) {
            return (
              <div key={tile.source} className={tileClass}>
                {content}
              </div>
            );
          }

          return (
            <a
              key={tile.source}
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className={`group ${tileClass}`}
            >
              {content}
            </a>
          );
        })}
      </div>
      <p className={`mt-2 text-xs ${daylight ? "text-[#84878F]" : "text-zinc-400"}`}>
        Averages from sold comps in our database. Tap a tile to search live listings on that marketplace.
      </p>
    </div>
  );
}
