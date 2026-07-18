"use client";

import type { CardOut } from "@tcgscan/sdk-ts";
import { searchCatalog } from "@tcgscan/sdk-ts";
import { cardDetailHref } from "@/lib/card-slug";
import { Hanken_Grotesk, IBM_Plex_Mono, Spectral } from "next/font/google";
import Image from "next/image";
import Link from "next/link";
import { useCallback, useState, type CSSProperties } from "react";

const display = Spectral({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
  variable: "--font-display",
});
const body = Hanken_Grotesk({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
  variable: "--font-body",
});
const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-num",
});

const daylightStyle = {
  "--bg": "#F7F6F2",
  "--surface": "#FFFFFF",
  "--surface2": "#F1EFE9",
  "--border": "#E4E1D8",
  "--border-soft": "#ECE9E0",
  "--text": "#17181C",
  "--text2": "#5B5F68",
  "--text3": "#84878F",
  "--accent": "#B6862E",
  "--accent2": "#D4A53D",
  "--accent-ink": "#1A1408",
  "--accent-soft": "rgba(182,134,46,0.10)",
  "--up": "#1E9A6B",
  "--down": "#D6444B",
  "--hold": "#B6862E",
  "--eyebrow": "#B6862E",
  "--radius": "18px",
  "--radius-sm": "11px",
  "--shadow": "0 1px 2px rgba(23,24,28,0.05)",
  "--panel": "#16181D",
  "--panel2": "#1E2128",
  "--panel-border": "#2A2E37",
  "--panel-text": "#F6F7F9",
  "--panel-text3": "#8C93A1",
  "--panel-gold": "#E0B94A",
  background: "var(--bg)",
  color: "var(--text)",
  fontFamily: "var(--font-body), system-ui, sans-serif",
} as CSSProperties;

const PAGE_SIZE = 48;

const GAMES = [
  { value: "", label: "All" },
  { value: "pokemon", label: "Pokémon" },
  { value: "mtg", label: "Magic" },
  { value: "yugioh", label: "Yu-Gi-Oh!" },
  { value: "one_piece", label: "One Piece" },
  { value: "lorcana", label: "Lorcana" },
  { value: "dragon_ball_fusion_world", label: "Dragon Ball" },
];

type SortKey = "recent" | "alpha" | "number";

const SORTS: { value: SortKey; label: string }[] = [
  { value: "recent", label: "Recently sold" },
  { value: "alpha", label: "Alphabetical" },
  { value: "number", label: "Number" },
];

function cardImage(card: CardOut): string | null {
  if (card.image_url) return card.image_url;
  const urls = card.image_urls;
  if (!urls) return null;
  const src = urls.large ?? urls.front ?? urls.small ?? urls.hires;
  return typeof src === "string" ? src : null;
}

function numKey(n: string | null | undefined): number {
  const match = /\d+/.exec(n ?? "");
  return match ? Number(match[0]) : Number.MAX_SAFE_INTEGER;
}

function PriceLabel({ card }: { card: CardOut }) {
  if (card.price_status === "available" && card.current_value != null) {
    return (
      <span
        className="text-[15px] font-extrabold tabular-nums text-[var(--text)]"
        style={{ fontFamily: "var(--font-num), monospace" }}
      >
        ${card.current_value.toFixed(2)}
      </span>
    );
  }
  return <span className="text-xs text-[var(--text3)]">Price pending</span>;
}

export function MarketClient() {
  const [q, setQ] = useState("");
  const [game, setGame] = useState("");
  const [sort, setSort] = useState<SortKey>("recent");
  const [results, setResults] = useState<CardOut[]>([]);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  const load = useCallback(
    async (nextOffset: number, append: boolean, gameOverride?: string) => {
      const activeGame = gameOverride !== undefined ? gameOverride : game;
      if (!q.trim() && !activeGame) return;
      setLoading(true);
      setError(null);
      setSearched(true);
      try {
        const out = await searchCatalog({
          q: q.trim() || undefined,
          game: activeGame || undefined,
          limit: PAGE_SIZE,
          offset: nextOffset,
        });
        setResults((prev) => (append ? [...prev, ...out] : out));
        setOffset(nextOffset + out.length);
        setHasMore(out.length === PAGE_SIZE);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Search failed");
        if (!append) setResults([]);
      } finally {
        setLoading(false);
      }
    },
    [q, game],
  );

  const onSearch = useCallback(() => {
    setOffset(0);
    void load(0, false);
  }, [load]);

  const onGameChip = useCallback(
    (value: string) => {
      setGame(value);
      setOffset(0);
      if (q.trim() || value) {
        void load(0, false, value);
      } else {
        setResults([]);
        setSearched(false);
        setHasMore(false);
      }
    },
    [load, q],
  );

  const sorted = [...results];
  if (sort === "alpha") sorted.sort((a, b) => a.name.localeCompare(b.name));
  if (sort === "number") {
    sorted.sort(
      (a, b) =>
        numKey(a.card_number ?? a.number) - numKey(b.card_number ?? b.number),
    );
  }

  return (
    <div
      className={`${display.variable} ${body.variable} ${mono.variable} min-h-[calc(100vh-57px)]`}
      style={daylightStyle}
    >
      <div className="mx-auto max-w-[1200px] px-6 pb-16 pt-10">
        <h1
          className="text-[32px] font-extrabold tracking-[-0.02em]"
          style={{ fontFamily: "var(--font-display), serif" }}
        >
          Market
        </h1>
        <p className="mt-1 text-[14.5px] text-[var(--text2)]">
          Search the catalogue across every game we track. Tap any card for prices and comps.
        </p>

        <div className="mt-[18px] flex items-center gap-2.5 rounded-[13px] border border-[var(--border)] bg-[var(--surface)] px-[18px] py-3.5 shadow-[var(--shadow)]">
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            className="shrink-0 text-[var(--text3)]"
            aria-hidden
          >
            <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
            <path d="m20 20-3-3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
          <input
            type="search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && onSearch()}
            placeholder="Search 1,000,000+ cards across 25+ games…"
            className="min-w-0 flex-1 bg-transparent text-[15px] text-[var(--text)] outline-none placeholder:text-[var(--text3)]"
          />
          <button
            type="button"
            onClick={onSearch}
            disabled={loading || (!q.trim() && !game)}
            className="whitespace-nowrap rounded-[11px] bg-[var(--accent)] px-4 py-2 text-[13px] font-bold text-[var(--accent-ink)] transition hover:opacity-90 disabled:opacity-40"
          >
            {loading && !results.length ? "Searching…" : "Search"}
          </button>
        </div>

        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap gap-2">
            {GAMES.map((g) => {
              const active = game === g.value;
              return (
                <button
                  key={g.value || "all"}
                  type="button"
                  onClick={() => onGameChip(g.value)}
                  className="whitespace-nowrap rounded-full border px-3.5 py-[7px] text-[12.5px] font-semibold transition"
                  style={{
                    borderColor: active ? "var(--accent)" : "var(--border)",
                    color: active ? "var(--accent-ink)" : "var(--text2)",
                    background: active ? "var(--accent)" : "var(--surface)",
                  }}
                >
                  {g.label}
                </button>
              );
            })}
          </div>
          <div className="flex flex-wrap gap-1.5">
            {SORTS.map((s) => {
              const active = sort === s.value;
              return (
                <button
                  key={s.value}
                  type="button"
                  onClick={() => setSort(s.value)}
                  className="whitespace-nowrap rounded-lg px-[11px] py-1.5 text-xs font-semibold"
                  style={{
                    color: active ? "var(--accent)" : "var(--text2)",
                    background: active ? "var(--surface2)" : "transparent",
                  }}
                >
                  {s.label}
                </button>
              );
            })}
          </div>
        </div>

        <p className="mt-4 text-xs text-[var(--text3)]">
          Catalogue metadata from imported sources. Marketplace pricing appears when sold comp data
          is available.
        </p>

        {error ? <p className="mt-3 text-sm text-[var(--down)]">{error}</p> : null}

        {searched && !loading && results.length === 0 && !error ? (
          <p className="mt-6 rounded-[var(--radius)] border border-dashed border-[var(--border)] px-4 py-10 text-center text-sm text-[var(--text3)]">
            No cards found. Try a different search or run a full catalogue import from{" "}
            <Link href="/admin/sources" className="font-semibold text-[var(--accent)] underline">
              Admin → Sources
            </Link>
            .
          </p>
        ) : null}

        {!searched && !loading ? (
          <div className="cc-panel mt-8 rounded-[var(--radius)] border border-[var(--panel-border)] bg-[var(--panel)] px-6 py-12 text-center text-[var(--panel-text)]">
            <p
              className="text-lg font-bold"
              style={{ fontFamily: "var(--font-display), serif" }}
            >
              Search any card
            </p>
            <p className="mx-auto mt-2 max-w-md text-sm text-[var(--panel-text3)]">
              Type a name, set, or number — or pick a game chip — to browse the catalogue.
            </p>
          </div>
        ) : null}

        <ul className="mt-7 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
          {sorted.map((card) => {
            const img = cardImage(card);
            return (
              <li key={card.id}>
                <Link
                  href={cardDetailHref(card)}
                  className="flex h-full flex-col overflow-hidden rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] shadow-[var(--shadow)] transition hover:border-[var(--accent)]"
                >
                  <div
                    className="relative aspect-[5/7] border-b border-[var(--border)]"
                    style={{
                      background: img
                        ? "var(--surface2)"
                        : "repeating-linear-gradient(135deg,var(--surface2),var(--surface2) 7px,var(--bg) 7px,var(--bg) 14px)",
                    }}
                  >
                    {img ? (
                      <Image
                        src={img}
                        alt={card.name}
                        fill
                        className="object-contain p-2"
                        sizes="180px"
                      />
                    ) : (
                      <div className="flex h-full items-center justify-center text-[10px] font-bold uppercase tracking-wider text-[var(--text3)]">
                        No image
                      </div>
                    )}
                    {card.rarity ? (
                      <span className="absolute left-2 top-2 whitespace-nowrap rounded-md border border-[var(--border)] bg-[var(--surface)] px-1.5 py-0.5 text-[10px] font-bold text-[var(--text2)]">
                        {card.rarity}
                      </span>
                    ) : null}
                  </div>
                  <div className="flex flex-1 flex-col gap-0.5 p-3">
                    <div className="truncate text-[13.5px] font-bold text-[var(--text)]">
                      {card.name}
                    </div>
                    <div className="truncate text-[11.5px] text-[var(--text3)]">
                      {card.set_name ?? card.set_code}
                      {card.card_number
                        ? ` · ${card.card_number}`
                        : card.number
                          ? ` · ${card.number}`
                          : ""}
                    </div>
                    <div className="mt-auto flex items-baseline justify-between pt-2">
                      <PriceLabel card={card} />
                      <span className="text-[11px] uppercase tracking-wide text-[var(--text3)]">
                        {card.game}
                      </span>
                    </div>
                  </div>
                </Link>
              </li>
            );
          })}
        </ul>

        {hasMore ? (
          <div className="mt-8 flex justify-center">
            <button
              type="button"
              disabled={loading}
              onClick={() => void load(offset, true)}
              className="rounded-[11px] border border-[var(--border)] bg-[var(--surface)] px-5 py-2.5 text-sm font-semibold text-[var(--text)] transition hover:bg-[var(--surface2)] disabled:opacity-50"
            >
              {loading ? "Loading…" : "Load more"}
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
