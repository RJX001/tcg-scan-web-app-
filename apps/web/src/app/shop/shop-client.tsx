"use client";

import { Button } from "@tcgscan/ui";
import Image from "next/image";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import type { ShopListingOut, ShopSort } from "@tcgscan/sdk-ts";
import { getShopListings } from "@tcgscan/sdk-ts";
import { GradeBadge } from "@/components/grade-badge";
import { useCurrency } from "@/lib/currency";

const PAGE_SIZE = 24;

const GAMES = [
  { value: "", label: "All games" },
  { value: "pokemon", label: "Pokemon" },
  { value: "mtg", label: "Magic" },
  { value: "yugioh", label: "Yu-Gi-Oh!" },
  { value: "lorcana", label: "Lorcana" },
  { value: "one_piece", label: "One Piece" },
  { value: "sports_baseball", label: "Baseball" },
  { value: "sports_basketball", label: "Basketball" },
];

const PLATFORMS = [
  { value: "", label: "All platforms" },
  { value: "ebay", label: "eBay" },
  { value: "tcgplayer", label: "TCGPlayer" },
  { value: "cardmarket", label: "Cardmarket" },
];

const GRADES = [
  { value: "", label: "All grades" },
  { value: "raw", label: "Raw only" },
  { value: "graded", label: "Graded only" },
  { value: "PSA", label: "PSA" },
  { value: "BGS", label: "Beckett (BGS)" },
  { value: "CGC", label: "CGC" },
  { value: "SGC", label: "SGC" },
];

const SORTS: { value: ShopSort; label: string }[] = [
  { value: "recent", label: "Recently added" },
  { value: "price_asc", label: "Price: low to high" },
  { value: "price_desc", label: "Price: high to low" },
];

function toIsoDate(d: string, endOfDay: boolean): string | undefined {
  if (!d) return undefined;
  return endOfDay ? `${d}T23:59:59Z` : `${d}T00:00:00Z`;
}

function thumb(listing: ShopListingOut): string | null {
  if (listing.image_url) return listing.image_url;
  const urls = listing.card?.image_urls;
  if (!urls) return null;
  const src = urls.small ?? urls.front ?? urls.hires;
  return typeof src === "string" ? src : null;
}

function listingTitle(listing: ShopListingOut): string {
  return listing.card?.name ?? listing.title ?? "Listing";
}

export function ShopClient() {
  const [q, setQ] = useState("");
  const [game, setGame] = useState("");
  const [source, setSource] = useState("");
  const [grade, setGrade] = useState("");
  const [sort, setSort] = useState<ShopSort>("recent");
  const [minPrice, setMinPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [minDate, setMinDate] = useState("");
  const [maxDate, setMaxDate] = useState("");
  const [showFilters, setShowFilters] = useState(false);
  const [rows, setRows] = useState<ShopListingOut[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const requestId = useRef(0);
  const { fmt: fmtMoney } = useCurrency();

  const load = useCallback(
    async (offset: number, append: boolean) => {
      const id = ++requestId.current;
      setLoading(true);
      setError(null);
      try {
        const out = await getShopListings({
          q: q.trim() || undefined,
          game: game || undefined,
          source: source || undefined,
          grade: grade || undefined,
          minPrice: minPrice ? Number(minPrice) : undefined,
          maxPrice: maxPrice ? Number(maxPrice) : undefined,
          listedAfter: toIsoDate(minDate, false),
          listedBefore: toIsoDate(maxDate, true),
          sort,
          limit: PAGE_SIZE,
          offset,
        });
        if (id !== requestId.current) return;
        setRows((prev) => (append ? [...prev, ...out] : out));
        setHasMore(out.length === PAGE_SIZE);
      } catch (e) {
        if (id !== requestId.current) return;
        setError(e instanceof Error ? e.message : "Failed to load listings");
        if (!append) setRows([]);
      } finally {
        if (id === requestId.current) setLoading(false);
      }
    },
    [q, game, source, grade, sort, minPrice, maxPrice, minDate, maxDate],
  );

  useEffect(() => {
    const t = setTimeout(() => void load(0, false), q || minPrice || maxPrice ? 300 : 0);
    return () => clearTimeout(t);
  }, [load, q, minPrice, maxPrice]);

  const activeFilterCount = [game, source, grade, minPrice, maxPrice, minDate, maxDate].filter(
    Boolean,
  ).length;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex gap-2">
        <input
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search listings by card, set, or number…"
          className="min-w-0 flex-1 rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm"
        />
        <Button
          variant="outline"
          onClick={() => setShowFilters((v) => !v)}
          aria-expanded={showFilters}
        >
          Filter{activeFilterCount > 0 ? ` (${activeFilterCount})` : ""}
        </Button>
      </div>

      {showFilters && (
        <div className="grid gap-2 rounded-xl border border-zinc-200 bg-white p-4 sm:grid-cols-2 lg:grid-cols-4">
          <input
            type="number"
            inputMode="decimal"
            min={0}
            value={minPrice}
            onChange={(e) => setMinPrice(e.target.value)}
            placeholder="Min price"
            className="rounded-lg border border-zinc-300 px-3 py-2 text-sm"
          />
          <input
            type="number"
            inputMode="decimal"
            min={0}
            value={maxPrice}
            onChange={(e) => setMaxPrice(e.target.value)}
            placeholder="Max price"
            className="rounded-lg border border-zinc-300 px-3 py-2 text-sm"
          />
          <input
            type="date"
            value={minDate}
            onChange={(e) => setMinDate(e.target.value)}
            className="rounded-lg border border-zinc-300 px-3 py-2 text-sm"
            aria-label="Listed after"
          />
          <input
            type="date"
            value={maxDate}
            onChange={(e) => setMaxDate(e.target.value)}
            className="rounded-lg border border-zinc-300 px-3 py-2 text-sm"
            aria-label="Listed before"
          />
          <select
            value={game}
            onChange={(e) => setGame(e.target.value)}
            className="rounded-lg border border-zinc-300 px-3 py-2 text-sm"
          >
            {GAMES.map((g) => (
              <option key={g.value} value={g.value}>
                {g.label}
              </option>
            ))}
          </select>
          <select
            value={source}
            onChange={(e) => setSource(e.target.value)}
            className="rounded-lg border border-zinc-300 px-3 py-2 text-sm"
          >
            {PLATFORMS.map((p) => (
              <option key={p.value} value={p.value}>
                {p.label}
              </option>
            ))}
          </select>
          <select
            value={grade}
            onChange={(e) => setGrade(e.target.value)}
            className="rounded-lg border border-zinc-300 px-3 py-2 text-sm"
          >
            {GRADES.map((g) => (
              <option key={g.value} value={g.value}>
                {g.label}
              </option>
            ))}
          </select>
          <Button
            variant="outline"
            onClick={() => {
              setGame("");
              setSource("");
              setGrade("");
              setMinPrice("");
              setMaxPrice("");
              setMinDate("");
              setMaxDate("");
            }}
          >
            Clear
          </Button>
        </div>
      )}

      <div className="flex flex-wrap gap-2">
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

      <ul className="divide-y divide-zinc-100 overflow-hidden rounded-xl border border-zinc-200 bg-white">
        {rows.map((l, i) => {
          const img = thumb(l);
          const title = listingTitle(l);
          return (
            <li key={`${l.listing_url ?? l.title ?? i}`} className="flex items-center gap-3 px-4 py-3">
              {img ? (
                <Image
                  src={img}
                  alt={title}
                  width={40}
                  height={56}
                  className="shrink-0 rounded border border-zinc-200 object-cover"
                />
              ) : (
                <div className="h-14 w-10 shrink-0 rounded border border-zinc-200 bg-zinc-100" />
              )}
              <div className="min-w-0 flex-1">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-zinc-400">
                  {l.source}
                </p>
                {l.card?.slug ? (
                  <Link
                    href={`/card/${l.card.slug}`}
                    className="block truncate font-medium hover:text-blue-700"
                  >
                    {title}
                    {l.card.number ? <span className="text-zinc-400"> #{l.card.number}</span> : null}
                  </Link>
                ) : (
                  <p className="truncate font-medium">{title}</p>
                )}
                <div className="mt-0.5 flex items-center gap-2">
                  <GradeBadge grade={l.grade} />
                  {l.card ? (
                    <span className="truncate text-xs text-zinc-500">
                      {l.card.set_name ?? l.card.set_code}
                    </span>
                  ) : null}
                </div>
              </div>
              <div className="shrink-0 text-right">
                <p className="text-[11px] uppercase tracking-wide text-zinc-400">Price</p>
                <p className="font-semibold">{fmtMoney(l.price_usd ?? l.price)}</p>
                {l.listing_url && (
                  <a
                    href={l.listing_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs font-medium text-blue-700 hover:underline"
                  >
                    View →
                  </a>
                )}
              </div>
            </li>
          );
        })}
        {!loading && rows.length === 0 && !error && (
          <li className="px-4 py-10 text-center text-sm text-zinc-500">
            Live marketplace listings are not enabled yet.{" "}
            <Link href="/cards" className="font-medium text-blue-700 hover:underline">
              Catalogue search
            </Link>{" "}
            is available.
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
