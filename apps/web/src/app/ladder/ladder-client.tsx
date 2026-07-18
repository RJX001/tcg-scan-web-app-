"use client";

import { Button } from "@tcgscan/ui";
import Image from "next/image";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import type { MarketMoverOut, MarketMoversSort, SavedSearchOut } from "@tcgscan/sdk-ts";
import {
  createSavedSearch,
  deleteSavedSearch,
  getMarketMovers,
  getSavedSearches,
} from "@tcgscan/sdk-ts";
import { GradeBadge } from "@/components/grade-badge";
import { useCurrency } from "@/lib/currency";
import { IndexChart } from "./index-chart";

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
  { value: "pokemon", label: "Pokemon" },
  { value: "mtg", label: "Magic" },
  { value: "yugioh", label: "Yu-Gi-Oh!" },
  { value: "lorcana", label: "Lorcana" },
  { value: "one_piece", label: "One Piece" },
  { value: "sports_baseball", label: "Baseball" },
  { value: "sports_basketball", label: "Basketball" },
  { value: "sports_football", label: "Football" },
];

const SORTS: { value: MarketMoversSort; label: string }[] = [
  { value: "change", label: "Top gainers" },
  { value: "change_asc", label: "Top losers" },
  { value: "price", label: "Highest price" },
  { value: "volume", label: "Most sales" },
  { value: "recent", label: "Recently sold" },
  { value: "market_cap", label: "Market cap" },
  { value: "pop", label: "Pop (Pro)" },
];

function thumb(mover: MarketMoverOut): string | null {
  const urls = mover.card.image_urls;
  if (!urls) return null;
  const src = urls.small ?? urls.front ?? urls.hires;
  return typeof src === "string" ? src : null;
}

function ChangeBadge({ pct }: { pct: number | null | undefined }) {
  if (pct == null) return <span className="text-sm text-zinc-400">—</span>;
  const up = pct >= 0;
  return (
    <span
      className={`inline-block rounded px-1.5 py-0.5 text-sm font-semibold ${
        up ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
      }`}
    >
      {up ? "+" : ""}
      {pct.toFixed(2)}%
    </span>
  );
}

export function LadderClient() {
  const [game, setGame] = useState("");
  const [sort, setSort] = useState<MarketMoversSort>("change");
  const [days, setDays] = useState(30);
  const [grade, setGrade] = useState("");
  const [q, setQ] = useState("");
  const [rows, setRows] = useState<MarketMoverOut[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState<SavedSearchOut[]>([]);
  const [saveName, setSaveName] = useState("");
  const [saveError, setSaveError] = useState<string | null>(null);
  const requestId = useRef(0);
  const { fmt: fmtMoney, fmtNum } = useCurrency();

  useEffect(() => {
    getSavedSearches()
      .then(setSaved)
      .catch(() => setSaved([]));
  }, []);

  const onSaveSearch = useCallback(async () => {
    const name = saveName.trim() || [game || "all", sort, q.trim()].filter(Boolean).join(" · ");
    setSaveError(null);
    try {
      const created = await createSavedSearch({
        name,
        params: {
          game: game || undefined,
          q: q.trim() || undefined,
          sort,
          days,
          grade: grade || undefined,
        },
      });
      setSaved((prev) => [created, ...prev.filter((s) => s.id !== created.id)]);
      setSaveName("");
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to save search";
      setSaveError(msg.includes("403") ? "Saved searches require Pro — upgrade at /account." : msg);
    }
  }, [saveName, game, sort, q, days, grade]);

  const onApplySearch = useCallback((s: SavedSearchOut) => {
    setGame(s.params.game ?? "");
    setSort((s.params.sort as MarketMoversSort) ?? "change");
    setDays(s.params.days ?? 30);
    setGrade(s.params.grade ?? "");
    setQ(s.params.q ?? "");
  }, []);

  const onDeleteSearch = useCallback(async (id: string) => {
    setSaved((prev) => prev.filter((s) => s.id !== id));
    try {
      await deleteSavedSearch(id);
    } catch {
      // best effort — list refreshes on next mount
    }
  }, []);

  const load = useCallback(
    async (offset: number, append: boolean) => {
      const id = ++requestId.current;
      setLoading(true);
      setError(null);
      try {
        const out = await getMarketMovers({
          game: game || undefined,
          q: q.trim() || undefined,
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
        const msg = e instanceof Error ? e.message : "Failed to load the ladder";
        setError(
          msg.includes("403") ? "This sort requires Pro — upgrade at /account." : msg,
        );
        if (!append) setRows([]);
      } finally {
        if (id === requestId.current) setLoading(false);
      }
    },
    [game, q, sort, days, grade],
  );

  useEffect(() => {
    const t = setTimeout(() => void load(0, false), q ? 300 : 0);
    return () => clearTimeout(t);
  }, [load, q]);

  const periodLabel = PERIODS.find((p) => p.days === days)?.label ?? `${days}d`;

  return (
    <div className="flex flex-col gap-4">
      <IndexChart game={game} />

      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium uppercase tracking-wide text-zinc-500">Window</span>
        {PERIODS.map((p) => (
          <button
            key={p.days}
            type="button"
            onClick={() => setDays(p.days)}
            className="whitespace-nowrap rounded-[7px] px-2.5 py-[5px] text-xs font-bold"
            style={{
              color: days === p.days ? "#B6862E" : "#84878F",
              background: days === p.days ? "#F1EFE9" : "transparent",
            }}
          >
            {p.label}
          </button>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium uppercase tracking-wide text-zinc-500">Grading</span>
        {GRADES.map((g) => (
          <button
            key={g.value}
            type="button"
            onClick={() => setGrade(g.value)}
            className="whitespace-nowrap rounded-full border px-3 py-1 text-xs font-semibold"
            style={{
              borderColor: grade === g.value ? "#B6862E" : "#E4E1D8",
              background: grade === g.value ? "#B6862E" : "#FFFFFF",
              color: grade === g.value ? "#1A1408" : "#5B5F68",
            }}
          >
            {g.label}
          </button>
        ))}
      </div>

      <div className="flex flex-col gap-2 sm:flex-row">
        <input
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Filter by name, set, or number…"
          className="flex-1 rounded-lg border border-zinc-300 px-3 py-2 text-sm"
        />
        <select
          value={game}
          onChange={(e) => setGame(e.target.value)}
          className="rounded-lg border border-zinc-300 px-3 py-2 text-sm sm:w-44"
        >
          {GAMES.map((g) => (
            <option key={g.value} value={g.value}>
              {g.label}
            </option>
          ))}
        </select>
        <select
          value={sort}
          onChange={(e) => setSort(e.target.value as MarketMoversSort)}
          className="rounded-lg border border-zinc-300 px-3 py-2 text-sm sm:w-48"
        >
          {SORTS.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
      </div>

      <div className="flex flex-wrap items-center gap-2 text-sm">
        {saved.map((s) => (
          <span
            key={s.id}
            className="inline-flex items-center gap-1 rounded-full border border-zinc-300 bg-zinc-50 pl-3"
          >
            <button
              type="button"
              className="py-1 text-zinc-700 hover:text-zinc-900"
              onClick={() => onApplySearch(s)}
            >
              {s.name}
            </button>
            <button
              type="button"
              aria-label={`Delete saved search ${s.name}`}
              className="px-2 py-1 text-zinc-400 hover:text-red-600"
              onClick={() => void onDeleteSearch(s.id)}
            >
              ×
            </button>
          </span>
        ))}
        <input
          type="text"
          value={saveName}
          onChange={(e) => setSaveName(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && void onSaveSearch()}
          placeholder="Name this search…"
          className="w-36 rounded-lg border border-zinc-300 px-2 py-1 text-sm"
        />
        <Button variant="outline" size="sm" onClick={() => void onSaveSearch()}>
          Save search
        </Button>
      </div>
      {saveError && <p className="text-sm text-amber-700">{saveError}</p>}

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="hidden grid-cols-[1fr_auto_auto_auto_auto] gap-4 px-4 text-xs uppercase tracking-wide text-zinc-500 sm:grid">
        <span>Card</span>
        <span className="w-16 text-right">Pop</span>
        <span className="w-20 text-right">Sales</span>
        <span className="w-24 text-right">{periodLabel} change</span>
        <span className="w-24 text-right">Last sold</span>
      </div>

      <ul
        className="divide-y overflow-hidden rounded-[18px] border"
        style={{ background: "#1E2128", borderColor: "#2A2E37", color: "#F6F7F9" }}
      >
        {rows.map((m) => {
          const img = thumb(m);
          return (
            <li key={m.card.id} style={{ borderColor: "#2A2E37" }}>
              <Link
                href={`/card/${m.card.slug}`}
                className="grid grid-cols-[1fr_auto] items-center gap-3 px-4 py-3 sm:grid-cols-[1fr_auto_auto_auto_auto] sm:gap-4"
                style={{ borderColor: "#2A2E37" }}
              >
                <div className="flex items-center gap-3">
                  {img ? (
                    <Image
                      src={img}
                      alt={m.card.name}
                      width={36}
                      height={50}
                      className="rounded border object-cover"
                      style={{ borderColor: "#2A2E37" }}
                    />
                  ) : (
                    <div
                      className="h-[50px] w-9 rounded border"
                      style={{ borderColor: "#2A2E37", background: "#252932" }}
                    />
                  )}
                  <div className="min-w-0">
                    <p className="truncate font-medium">
                      {m.card.name}
                      {m.card.number ? (
                        <span className="ml-1" style={{ color: "#8C93A1" }}>
                          #{m.card.number}
                        </span>
                      ) : null}
                    </p>
                    <div className="mt-0.5 flex items-center gap-2">
                      <GradeBadge grade={m.last_sold_grade} />
                      <span className="truncate text-xs" style={{ color: "#8C93A1" }}>
                        {m.card.set_name ?? m.card.set_code} · {m.card.rarity ?? m.card.game}
                      </span>
                    </div>
                  </div>
                </div>
                <span
                  className="hidden w-16 text-right text-sm sm:block"
                  style={{ color: "#BAC0CB" }}
                >
                  {fmtNum(m.pop_count)}
                </span>
                <span
                  className="hidden w-20 text-right text-sm sm:block"
                  style={{ color: "#BAC0CB" }}
                >
                  {m.sales_count}
                </span>
                <span className="hidden w-24 text-right sm:block">
                  <ChangeBadge pct={m.change_pct} />
                </span>
                <span className="w-24 text-right">
                  <span className="block text-sm font-semibold">{fmtMoney(m.last_sold_usd)}</span>
                  <span className="block sm:hidden">
                    <ChangeBadge pct={m.change_pct} />
                  </span>
                </span>
              </Link>
            </li>
          );
        })}
        {!loading && rows.length === 0 && !error && (
          <li className="px-4 py-8 text-center text-sm" style={{ color: "#8C93A1" }}>
            No sales data yet. Run <code className="rounded px-1" style={{ background: "#252932" }}>pnpm db:seed</code>{" "}
            for demo data, or adjust your filters.
          </li>
        )}
      </ul>

      <div className="flex justify-center">
        {loading ? (
          <p className="text-sm text-zinc-500">Loading…</p>
        ) : hasMore ? (
          <Button variant="outline" onClick={() => void load(rows.length, true)}>
            Load more
          </Button>
        ) : null}
      </div>
    </div>
  );
}
