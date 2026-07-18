"use client";

import {
  exportPortfolioCsv,
  getPortfolio,
  getPortfolioSummary,
  removeFromPortfolio,
} from "@tcgscan/sdk-ts";
import Image from "next/image";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useCurrency } from "@/lib/currency";

const PF_FILTERS = [
  { label: "All", match: null as string | null },
  { label: "Pokémon", match: "pokemon" },
  { label: "Magic", match: "mtg" },
  { label: "Yu-Gi-Oh!", match: "yugioh" },
  { label: "One Piece", match: "one_piece" },
  { label: "Lorcana", match: "lorcana" },
  { label: "Riftbound", match: "riftbound" },
  { label: "Sports", match: "sports" },
  { label: "Sealed", match: "sealed" },
] as const;

type VerdictTone = "buy" | "hold" | "sell";

function matchesFilter(game: string, filter: string | null): boolean {
  if (!filter) return true;
  const g = game.toLowerCase();
  if (filter === "sports") return g.startsWith("sports");
  if (filter === "sealed") return g.includes("sealed");
  return g === filter;
}

function itemValue(item: Awaited<ReturnType<typeof getPortfolio>>[number]): number | null {
  if (item.estimated_value_usd == null) return null;
  return item.estimated_value_usd * (item.quantity || 1);
}

function itemPnl(item: Awaited<ReturnType<typeof getPortfolio>>[number]): number | null {
  const value = itemValue(item);
  if (value == null || item.cost_basis_usd == null) return null;
  return value - item.cost_basis_usd;
}

function verdictFromPnl(pnl: number | null, cost: number | null | undefined): VerdictTone {
  if (pnl == null || cost == null || cost === 0) return "hold";
  const pct = (pnl / cost) * 100;
  if (pct <= -15) return "buy";
  if (pct >= 20) return "sell";
  return "hold";
}

const VERDICT_STYLE: Record<VerdictTone, { label: string; bg: string; color: string }> = {
  buy: { label: "▲ Buy", bg: "rgba(52,212,153,0.16)", color: "#34D499" },
  hold: { label: "● Hold", bg: "rgba(224,185,74,0.16)", color: "#E0B94A" },
  sell: { label: "▼ Sell", bg: "rgba(255,107,112,0.16)", color: "#FF6B70" },
};

function thumbUrl(urls: Record<string, unknown> | null | undefined, fallback?: string | null): string | null {
  if (fallback) return fallback;
  if (!urls) return null;
  const src = urls.small ?? urls.front ?? urls.hires;
  return typeof src === "string" ? src : null;
}

function Chip({
  active,
  label,
  onClick,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="shrink-0 whitespace-nowrap rounded-full border px-[13px] py-[7px] text-[12.5px] font-semibold transition-colors"
      style={{
        borderColor: active ? "#B6862E" : "#E4E1D8",
        background: active ? "#B6862E" : "#FFFFFF",
        color: active ? "#1A1408" : "#5B5F68",
      }}
    >
      {label}
    </button>
  );
}

export function PortfolioClient() {
  const { fmt: fmtMoney } = useCurrency();
  const [items, setItems] = useState<Awaited<ReturnType<typeof getPortfolio>>>([]);
  const [summary, setSummary] = useState<Awaited<ReturnType<typeof getPortfolioSummary>> | null>(
    null,
  );
  const [filter, setFilter] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setItems(await getPortfolio());
      setSummary(await getPortfolioSummary());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load portfolio");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const filtered = useMemo(
    () => items.filter((item) => matchesFilter(item.card.game, filter)),
    [items, filter],
  );

  const totalValue = summary?.estimated_value_usd ?? null;
  const totalCost = summary?.total_cost_basis_usd ?? null;
  const totalPnl =
    totalValue != null && totalCost != null ? totalValue - totalCost : null;
  const pnlPct =
    totalPnl != null && totalCost != null && totalCost > 0
      ? (totalPnl / totalCost) * 100
      : null;

  const watchlist = useMemo(() => {
    return items
      .map((item) => {
        const pnl = itemPnl(item);
        const tone = verdictFromPnl(pnl, item.cost_basis_usd);
        return { item, pnl, tone };
      })
      .filter((x) => x.tone !== "hold")
      .sort((a, b) => Math.abs(b.pnl ?? 0) - Math.abs(a.pnl ?? 0))
      .slice(0, 3);
  }, [items]);

  async function remove(id: string) {
    await removeFromPortfolio(id);
    await load();
  }

  async function exportCsv() {
    try {
      const blob = await exportPortfolioCsv();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "tcgscan-portfolio.csv";
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Export failed");
    }
  }

  if (loading) {
    return <p className="text-sm" style={{ color: "#5B5F68" }}>Loading vault…</p>;
  }
  if (error) {
    return <p className="text-sm" style={{ color: "#D6444B" }}>{error}</p>;
  }

  return (
    <div className="space-y-0">
      <div className="flex flex-wrap items-end justify-between gap-5 pb-2 pt-2">
        <div>
          <h1
            className="text-[32px] font-extrabold tracking-[-0.02em]"
            style={{ fontFamily: "var(--font-display), Georgia, serif", color: "#17181C" }}
          >
            Vault
          </h1>
          <p className="mt-1 text-[14.5px]" style={{ color: "#5B5F68" }}>
            Your collection, valued from live sold data — with verdicts on what to do next.
          </p>
        </div>
        {items.length > 0 && (
          <button
            type="button"
            onClick={() => void exportCsv()}
            className="rounded-[10px] px-4 py-[9px] text-[13px] font-bold"
            style={{ background: "#B6862E", color: "#1A1408" }}
          >
            Export CSV
          </button>
        )}
      </div>

      <div className="mt-3.5 flex flex-wrap gap-2">
        {PF_FILTERS.map((f) => (
          <Chip
            key={f.label}
            label={f.label}
            active={filter === f.match}
            onClick={() => setFilter(f.match)}
          />
        ))}
      </div>

      <div className="mt-6 grid gap-3.5 md:grid-cols-[1.4fr_1fr_1fr]">
        <div
          className="rounded-[18px] border p-[22px] shadow-[0_1px_2px_rgba(23,24,28,0.05)]"
          style={{ background: "#FFFFFF", borderColor: "#E4E1D8" }}
        >
          <div className="text-[12.5px]" style={{ color: "#5B5F68" }}>
            Total value
          </div>
          <div
            className="mt-1.5 text-[38px] font-extrabold tracking-[-0.02em] tabular-nums"
            style={{ fontFamily: "var(--font-mono), monospace", color: "#17181C" }}
          >
            {fmtMoney(totalValue)}
          </div>
          <div className="mt-1 text-sm font-bold" style={{ color: "#1E9A6B" }}>
            {summary?.item_count ?? 0} card{(summary?.item_count ?? 0) === 1 ? "" : "s"} in vault
          </div>
          <svg
            viewBox="0 0 600 90"
            width="100%"
            height="80"
            preserveAspectRatio="none"
            className="mt-3.5 block"
            aria-hidden
          >
            <defs>
              <linearGradient id="ccpf" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" stopColor="#1E9A6B" stopOpacity="0.28" />
                <stop offset="1" stopColor="#1E9A6B" stopOpacity="0" />
              </linearGradient>
            </defs>
            <path
              d="M0 70 L60 66 L120 72 L180 58 L240 62 L300 48 L360 52 L420 38 L480 44 L540 26 L600 18 L600 90 L0 90Z"
              fill="url(#ccpf)"
            />
            <path
              d="M0 70 L60 66 L120 72 L180 58 L240 62 L300 48 L360 52 L420 38 L480 44 L540 26 L600 18"
              fill="none"
              stroke="#1E9A6B"
              strokeWidth="2"
            />
          </svg>
        </div>

        <div
          className="rounded-[18px] border p-[22px] shadow-[0_1px_2px_rgba(23,24,28,0.05)]"
          style={{ background: "#FFFFFF", borderColor: "#E4E1D8" }}
        >
          <div className="text-[12.5px]" style={{ color: "#5B5F68" }}>
            Unrealised P&amp;L
          </div>
          <div
            className="mt-2 text-[26px] font-extrabold tabular-nums"
            style={{
              fontFamily: "var(--font-mono), monospace",
              color: totalPnl != null && totalPnl < 0 ? "#D6444B" : "#1E9A6B",
            }}
          >
            {totalPnl == null
              ? "—"
              : `${totalPnl >= 0 ? "▲" : "▼"} ${fmtMoney(Math.abs(totalPnl))}`}
          </div>
          {pnlPct != null && (
            <div
              className="mt-1 text-[12.5px] font-bold"
              style={{ color: pnlPct >= 0 ? "#1E9A6B" : "#D6444B" }}
            >
              {pnlPct >= 0 ? "+" : ""}
              {pnlPct.toFixed(0)}% on cost
            </div>
          )}
          <div className="mt-3.5 text-[12.5px]" style={{ color: "#5B5F68" }}>
            Cost basis{" "}
            <b
              className="font-bold"
              style={{ color: "#17181C", fontFamily: "var(--font-mono), monospace" }}
            >
              {fmtMoney(totalCost)}
            </b>
          </div>
        </div>

        <div
          className="rounded-[18px] border p-[22px] shadow-[0_1px_2px_rgba(23,24,28,0.05)]"
          style={{ background: "#FFFFFF", borderColor: "#E4E1D8" }}
        >
          <div className="text-[12.5px]" style={{ color: "#5B5F68" }}>
            Verdict watchlist
          </div>
          <div
            className="mt-2 text-[22px] font-extrabold"
            style={{ fontFamily: "var(--font-display), Georgia, serif", color: "#17181C" }}
          >
            {watchlist.length === 0
              ? "Nothing to act on"
              : `${watchlist.length} to act on`}
          </div>
          <div className="mt-3 flex flex-col gap-2 text-[12.5px]" style={{ color: "#17181C" }}>
            {watchlist.length === 0 ? (
              <span style={{ color: "#84878F" }}>Holdings look stable vs cost basis.</span>
            ) : (
              watchlist.map(({ item, tone }) => {
                const style = VERDICT_STYLE[tone];
                return (
                  <span key={item.id} className="flex items-center gap-2">
                    <span
                      className="rounded-md px-2 py-0.5 text-[11px] font-bold"
                      style={{ background: style.bg, color: style.color }}
                    >
                      {style.label}
                    </span>
                    <span className="truncate">{item.card.name}</span>
                  </span>
                );
              })
            )}
          </div>
        </div>
      </div>

      <div
        className="mb-0 mt-[30px] text-base font-bold"
        style={{ fontFamily: "var(--font-display), Georgia, serif", color: "#17181C" }}
      >
        Holdings
      </div>

      <div
        className="mt-3.5 overflow-hidden rounded-[18px] border shadow-[0_1px_2px_rgba(23,24,28,0.05)]"
        style={{ background: "#1E2128", borderColor: "#2A2E37", color: "#F6F7F9" }}
      >
        {filtered.length === 0 ? (
          <div className="px-[18px] py-10 text-center text-sm" style={{ color: "#8C93A1" }}>
            {items.length === 0 ? (
              <>
                No cards yet.{" "}
                <Link href="/search" className="underline" style={{ color: "#E0B94A" }}>
                  Search
                </Link>{" "}
                or scan a card and tap Add to portfolio.
              </>
            ) : (
              "No holdings match this filter."
            )}
          </div>
        ) : (
          <>
            <div
              className="hidden gap-3 border-b px-[18px] py-3 text-[10.5px] font-bold uppercase tracking-[0.06em] sm:grid sm:grid-cols-[34px_2.2fr_1fr_1fr_1fr_1.1fr_auto]"
              style={{ borderColor: "#2A2E37", color: "#8C93A1" }}
            >
              <div>#</div>
              <div>Card</div>
              <div>Value</div>
              <div>Cost</div>
              <div>P&amp;L</div>
              <div>Verdict</div>
              <div />
            </div>
            {filtered.map((item, i) => {
              const value = itemValue(item);
              const pnl = itemPnl(item);
              const tone = verdictFromPnl(pnl, item.cost_basis_usd);
              const v = VERDICT_STYLE[tone];
              const img = thumbUrl(item.card.image_urls, item.card.image_url);
              return (
                <div
                  key={item.id}
                  className="grid grid-cols-[1fr_auto] items-center gap-3 border-b px-[18px] py-[13px] sm:grid-cols-[34px_2.2fr_1fr_1fr_1fr_1.1fr_auto]"
                  style={{ borderColor: "#2A2E37" }}
                >
                  <div
                    className="hidden text-[13px] font-bold tabular-nums sm:block"
                    style={{ color: "#8C93A1", fontFamily: "var(--font-mono), monospace" }}
                  >
                    {i + 1}
                  </div>
                  <Link
                    href={`/card/${item.card.slug}`}
                    className="flex min-w-0 items-center gap-3"
                  >
                    {img ? (
                      <Image
                        src={img}
                        alt={item.card.name}
                        width={32}
                        height={44}
                        className="h-11 w-8 shrink-0 rounded-md border object-cover"
                        style={{ borderColor: "#2A2E37", background: "#252932" }}
                      />
                    ) : (
                      <div
                        className="h-11 w-8 shrink-0 rounded-md border"
                        style={{ background: "#252932", borderColor: "#2A2E37" }}
                      />
                    )}
                    <div className="min-w-0">
                      <div className="truncate text-sm font-semibold">{item.card.name}</div>
                      <div className="mt-0.5 truncate text-xs" style={{ color: "#8C93A1" }}>
                        {item.card.set_name ?? item.card.set_code ?? item.card.game}
                        {item.quantity > 1 ? ` · ×${item.quantity}` : ""}
                      </div>
                    </div>
                  </Link>
                  <div
                    className="hidden text-sm font-bold tabular-nums sm:block"
                    style={{ fontFamily: "var(--font-mono), monospace" }}
                  >
                    {fmtMoney(value)}
                  </div>
                  <div
                    className="hidden tabular-nums sm:block"
                    style={{ color: "#BAC0CB", fontFamily: "var(--font-mono), monospace" }}
                  >
                    {fmtMoney(item.cost_basis_usd)}
                  </div>
                  <div
                    className="hidden font-bold tabular-nums sm:block"
                    style={{
                      fontFamily: "var(--font-mono), monospace",
                      color: pnl == null ? "#8C93A1" : pnl >= 0 ? "#34D499" : "#FF6B70",
                    }}
                  >
                    {pnl == null
                      ? "—"
                      : `${pnl >= 0 ? "+" : "−"}${fmtMoney(Math.abs(pnl))}`}
                  </div>
                  <div className="hidden sm:block">
                    <span
                      className="rounded-[7px] px-2.5 py-1 text-[11.5px] font-bold"
                      style={{ background: v.bg, color: v.color }}
                    >
                      {v.label}
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => void remove(item.id)}
                    className="text-xs font-semibold"
                    style={{ color: "#8C93A1" }}
                  >
                    Remove
                  </button>
                </div>
              );
            })}
          </>
        )}
      </div>
    </div>
  );
}
