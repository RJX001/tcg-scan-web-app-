"use client";

import Image from "next/image";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import type { IndexSummaryOut, MarketMoverOut, MarketMoversSort } from "@tcgscan/sdk-ts";
import { getIndexes, getMarketMovers } from "@tcgscan/sdk-ts";
import { GradeBadge } from "@/components/grade-badge";
import { useCurrency } from "@/lib/currency";
import { IndexChart } from "../ladder/index-chart";

const PAGE_SIZE = 20;

const PERIODS = [
  { label: "1W", days: 7 },
  { label: "1M", days: 30 },
  { label: "3M", days: 90 },
  { label: "1Y", days: 365 },
];

const GRADES = [
  { value: "", label: "All grades" },
  { value: "raw", label: "Raw" },
  { value: "graded", label: "Graded" },
  { value: "PSA", label: "PSA" },
  { value: "BGS", label: "Beckett" },
  { value: "CGC", label: "CGC" },
  { value: "SGC", label: "SGC" },
];

const GAMES = [
  { value: "", label: "All games" },
  { value: "pokemon", label: "Pokémon" },
  { value: "mtg", label: "Magic" },
  { value: "yugioh", label: "Yu-Gi-Oh!" },
  { value: "lorcana", label: "Lorcana" },
  { value: "one_piece", label: "One Piece" },
  { value: "sports_baseball", label: "Baseball" },
  { value: "sports_basketball", label: "Basketball" },
  { value: "sports_football", label: "Football" },
];

const SORTS: { value: MarketMoversSort; label: string; tab: string }[] = [
  { value: "change", label: "Top gainers", tab: "movers" },
  { value: "change_asc", label: "Top losers", tab: "losers" },
  { value: "price", label: "Highest price", tab: "highest" },
  { value: "volume", label: "Most sales", tab: "sales" },
  { value: "recent", label: "Recently sold", tab: "recent" },
  { value: "market_cap", label: "Market cap", tab: "cap" },
  { value: "pop", label: "Pop (Pro)", tab: "pop" },
];

const SPARK_UP = "M0 22 L20 20 L40 24 L60 14 L80 16 L100 8 L120 4";
const SPARK_DOWN = "M0 6 L20 10 L40 8 L60 16 L80 14 L100 22 L120 26";

function thumb(mover: MarketMoverOut): string | null {
  const urls = mover.card.image_urls;
  if (!urls) return null;
  const src = urls.small ?? urls.front ?? urls.hires;
  return typeof src === "string" ? src : null;
}

function momentumTag(pct: number | null | undefined): { label: string; bg: string; color: string } {
  if (pct == null) return { label: "FLAT", bg: "rgba(224,185,74,0.16)", color: "#E0B94A" };
  if (pct >= 3) return { label: "HOT", bg: "rgba(30,154,107,0.13)", color: "#1E9A6B" };
  if (pct <= -3) return { label: "COLD", bg: "rgba(214,68,75,0.13)", color: "#D6444B" };
  return { label: "STEADY", bg: "rgba(182,134,46,0.13)", color: "#B6862E" };
}

function Chip({
  active,
  label,
  onClick,
  pill = true,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
  pill?: boolean;
}) {
  if (!pill) {
    return (
      <button
        type="button"
        onClick={onClick}
        className="whitespace-nowrap rounded-[7px] px-2.5 py-[5px] text-xs font-bold"
        style={{
          color: active ? "#B6862E" : "#84878F",
          background: active ? "#F1EFE9" : "transparent",
        }}
      >
        {label}
      </button>
    );
  }
  return (
    <button
      type="button"
      onClick={onClick}
      className="shrink-0 whitespace-nowrap rounded-full border px-[11px] py-[5px] text-xs font-semibold"
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

export function IndexesClient() {
  const [days, setDays] = useState(30);
  const [grade, setGrade] = useState("");
  const [game, setGame] = useState("");
  const [sort, setSort] = useState<MarketMoversSort>("change");
  const [indexes, setIndexes] = useState<IndexSummaryOut[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [rows, setRows] = useState<MarketMoverOut[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [loadingIndexes, setLoadingIndexes] = useState(true);
  const [loadingMovers, setLoadingMovers] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const requestId = useRef(0);
  const { fmt: fmtMoney } = useCurrency();

  useEffect(() => {
    let cancelled = false;
    setLoadingIndexes(true);
    getIndexes(days)
      .then((out) => {
        if (!cancelled) setIndexes(out);
      })
      .catch(() => {
        if (!cancelled) setIndexes([]);
      })
      .finally(() => {
        if (!cancelled) setLoadingIndexes(false);
      });
    return () => {
      cancelled = true;
    };
  }, [days]);

  const loadMovers = useCallback(
    async (offset: number, append: boolean) => {
      const id = ++requestId.current;
      setLoadingMovers(true);
      setError(null);
      try {
        const out = await getMarketMovers({
          game: game || undefined,
          grade: grade || undefined,
          sort,
          days,
          limit: PAGE_SIZE,
          offset,
        });
        if (id !== requestId.current) return;
        setRows((prev) => (append ? [...prev, ...out] : out));
        setHasMore(out.length === PAGE_SIZE);
      } catch (e) {
        if (id !== requestId.current) return;
        const msg = e instanceof Error ? e.message : "Failed to load movers";
        setError(
          msg.includes("403") ? "This sort requires Pro — upgrade at /account." : msg,
        );
        if (!append) setRows([]);
      } finally {
        if (id === requestId.current) setLoadingMovers(false);
      }
    },
    [game, grade, sort, days],
  );

  useEffect(() => {
    void loadMovers(0, false);
  }, [loadMovers]);

  const periodLabel = PERIODS.find((p) => p.days === days)?.label ?? `${days}d`;

  return (
    <div className="flex flex-col gap-0">
      <div className="flex flex-wrap items-end justify-between gap-5 pb-2">
        <div>
          <h1
            className="text-[32px] font-extrabold tracking-[-0.02em]"
            style={{ fontFamily: "var(--font-display), Georgia, serif", color: "#17181C" }}
          >
            Indexes
          </h1>
          <p className="mt-1 text-[14.5px]" style={{ color: "#5B5F68" }}>
            The market at a glance — last sold prices, monthly movement and sales volume across
            every card we track.
          </p>
        </div>
      </div>

      <div className="mt-1.5 flex flex-wrap gap-[18px]">
        <div className="flex flex-wrap items-center gap-1.5">
          <span
            className="text-[11px] font-bold uppercase tracking-[0.08em]"
            style={{ color: "#84878F" }}
          >
            Window
          </span>
          {PERIODS.map((p) => (
            <Chip
              key={p.days}
              pill={false}
              label={p.label}
              active={days === p.days}
              onClick={() => setDays(p.days)}
            />
          ))}
        </div>
        <div className="flex flex-wrap gap-1.5">
          {GRADES.map((g) => (
            <Chip
              key={g.value}
              label={g.label}
              active={grade === g.value}
              onClick={() => setGrade(g.value)}
            />
          ))}
        </div>
        <div className="flex flex-wrap gap-1.5">
          {GAMES.map((g) => (
            <Chip
              key={g.value}
              label={g.label}
              active={game === g.value}
              onClick={() => setGame(g.value)}
            />
          ))}
        </div>
      </div>

      <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {indexes.map((idx) => {
          const pct = idx.change_pct;
          const up = (pct ?? 0) >= 0;
          const changeC = pct == null ? "#84878F" : up ? "#1E9A6B" : "#D6444B";
          const seg = momentumTag(pct);
          const open = expanded === idx.key;
          return (
            <button
              key={idx.key}
              type="button"
              onClick={() => setExpanded((cur) => (cur === idx.key ? null : idx.key))}
              className="rounded-[11px] border p-[15px] text-left shadow-[0_1px_2px_rgba(23,24,28,0.05)] transition-shadow hover:shadow-md"
              style={{
                background: open ? "#F1EFE9" : "#FFFFFF",
                borderColor: open ? "#B6862E" : "#E4E1D8",
              }}
              aria-expanded={open}
            >
              <div className="text-[13px] font-bold" style={{ color: "#17181C" }}>
                {idx.name}
              </div>
              <div
                className="mt-2 text-[19px] font-extrabold tabular-nums"
                style={{ fontFamily: "var(--font-mono), monospace", color: "#17181C" }}
              >
                {idx.latest_value != null ? idx.latest_value.toFixed(1) : "—"}
              </div>
              <div
                className="mt-0.5 text-[11.5px] font-bold tabular-nums"
                style={{ color: changeC, fontFamily: "var(--font-mono), monospace" }}
              >
                {pct == null ? "—" : `${up ? "+" : ""}${pct.toFixed(2)}%`}
              </div>
              <svg
                width="100%"
                height="30"
                viewBox="0 0 120 30"
                preserveAspectRatio="none"
                className="mt-2 block"
                aria-hidden
              >
                <path
                  d={up ? SPARK_UP : SPARK_DOWN}
                  fill="none"
                  stroke={changeC}
                  strokeWidth="2"
                />
              </svg>
              <div
                className="mt-2.5 inline-block rounded-md px-[7px] py-[3px] text-[10px] font-bold tracking-[0.04em]"
                style={{ background: seg.bg, color: seg.color }}
              >
                {seg.label}
              </div>
            </button>
          );
        })}
        {!loadingIndexes && indexes.length === 0 && (
          <p className="col-span-full py-6 text-center text-sm" style={{ color: "#84878F" }}>
            Market indexes will appear after price observations are collected.
          </p>
        )}
      </div>

      {expanded && (
        <div className="mt-4">
          <IndexChart game={expanded === "all" ? "" : expanded} />
        </div>
      )}

      <div className="mt-5 flex gap-1 overflow-x-auto border-b" style={{ borderColor: "#E4E1D8" }}>
        {SORTS.map((s) => {
          const active = sort === s.value;
          return (
            <button
              key={s.value}
              type="button"
              onClick={() => setSort(s.value)}
              className="shrink-0 whitespace-nowrap px-3.5 py-[11px] text-[13.5px] font-semibold"
              style={{
                color: active ? "#17181C" : "#5B5F68",
                borderBottom: active ? "2px solid #B6862E" : "2px solid transparent",
                marginBottom: -1,
              }}
            >
              {s.label}
            </button>
          );
        })}
      </div>

      {error && (
        <p className="mt-3 text-sm" style={{ color: "#D6444B" }}>
          {error}
        </p>
      )}

      <div
        className="mt-[18px] overflow-hidden rounded-[18px] border shadow-[0_1px_2px_rgba(23,24,28,0.05)]"
        style={{ background: "#1E2128", borderColor: "#2A2E37", color: "#F6F7F9" }}
      >
        <div
          className="hidden gap-3 border-b px-[18px] py-3 text-[10.5px] font-bold uppercase tracking-[0.06em] sm:grid sm:grid-cols-[34px_2.4fr_1fr_1fr_1fr_1.1fr]"
          style={{ borderColor: "#2A2E37", color: "#8C93A1" }}
        >
          <div>#</div>
          <div>Card</div>
          <div>Value</div>
          <div>{periodLabel}</div>
          <div>Sales</div>
          <div>Grade</div>
        </div>
        {rows.map((m, i) => {
          const img = thumb(m);
          const pct = m.change_pct;
          const up = (pct ?? 0) >= 0;
          const changeC = pct == null ? "#8C93A1" : up ? "#34D499" : "#FF6B70";
          return (
            <Link
              key={m.card.id}
              href={`/card/${m.card.slug}`}
              className="grid grid-cols-[1fr_auto] items-center gap-3 border-b px-[18px] py-[13px] sm:grid-cols-[34px_2.4fr_1fr_1fr_1fr_1.1fr]"
              style={{ borderColor: "#2A2E37" }}
            >
              <div
                className="hidden text-[13px] font-bold tabular-nums sm:block"
                style={{ color: "#8C93A1", fontFamily: "var(--font-mono), monospace" }}
              >
                {i + 1}
              </div>
              <div className="flex min-w-0 items-center gap-3">
                {img ? (
                  <Image
                    src={img}
                    alt={m.card.name}
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
                  <div className="truncate text-sm font-semibold">{m.card.name}</div>
                  <div className="mt-0.5 truncate text-xs" style={{ color: "#8C93A1" }}>
                    {m.card.set_name ?? m.card.set_code ?? m.card.game}
                  </div>
                </div>
              </div>
              <div
                className="hidden text-sm font-bold tabular-nums sm:block"
                style={{ fontFamily: "var(--font-mono), monospace" }}
              >
                {fmtMoney(m.last_sold_usd)}
              </div>
              <div
                className="text-right text-[13px] font-semibold tabular-nums sm:text-left"
                style={{ color: changeC, fontFamily: "var(--font-mono), monospace" }}
              >
                {pct == null ? "—" : `${up ? "+" : ""}${pct.toFixed(2)}%`}
              </div>
              <div
                className="hidden text-[13px] tabular-nums sm:block"
                style={{ color: "#BAC0CB", fontFamily: "var(--font-mono), monospace" }}
              >
                {m.sales_count}
              </div>
              <div className="hidden sm:block">
                <GradeBadge grade={m.last_sold_grade} />
              </div>
            </Link>
          );
        })}
        {!loadingMovers && rows.length === 0 && !error && (
          <div className="px-[18px] py-10 text-center text-sm" style={{ color: "#8C93A1" }}>
            No sales data yet. Adjust filters or seed demo data.
          </div>
        )}
      </div>

      <div className="mt-4 flex justify-center">
        {loadingMovers ? (
          <p className="text-sm" style={{ color: "#84878F" }}>
            Loading…
          </p>
        ) : hasMore ? (
          <button
            type="button"
            onClick={() => void loadMovers(rows.length, true)}
            className="rounded-[10px] border px-4 py-2 text-[13px] font-semibold"
            style={{ borderColor: "#E4E1D8", background: "#FFFFFF", color: "#17181C" }}
          >
            Load more
          </button>
        ) : null}
      </div>
    </div>
  );
}
