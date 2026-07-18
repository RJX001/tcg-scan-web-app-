"use client";

import Image from "next/image";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { SaleBrowseOut, ShopSort } from "@tcgscan/sdk-ts";
import { getSalesBrowse } from "@tcgscan/sdk-ts";
import { formatGradeLabel } from "@/lib/sales-display";

const PAGE_SIZE = 24;

type ChipFilter =
  | { kind: "all" }
  | { kind: "game"; value: string }
  | { kind: "grade"; value: string };

const FILTER_CHIPS: { label: string; filter: ChipFilter }[] = [
  { label: "All", filter: { kind: "all" } },
  { label: "Pokémon", filter: { kind: "game", value: "pokemon" } },
  { label: "Magic", filter: { kind: "game", value: "mtg" } },
  { label: "Yu-Gi-Oh!", filter: { kind: "game", value: "yugioh" } },
  { label: "One Piece", filter: { kind: "game", value: "one_piece" } },
  { label: "Graded", filter: { kind: "grade", value: "graded" } },
  { label: "Raw", filter: { kind: "grade", value: "raw" } },
];

type ShowcaseSort = "recent" | "alpha" | "number";

const SHOWCASE_SORTS: { value: ShowcaseSort; label: string }[] = [
  { value: "recent", label: "Recently sold" },
  { value: "alpha", label: "Alphabetical" },
  { value: "number", label: "Number" },
];

function fmtNative(n: number, currency: string) {
  try {
    return new Intl.NumberFormat(undefined, { style: "currency", currency }).format(n);
  } catch {
    return `${currency} ${n.toFixed(2)}`;
  }
}

function thumb(sale: SaleBrowseOut): string | null {
  const urls = sale.card.image_urls;
  if (!urls) return null;
  const src = urls.small ?? urls.front ?? urls.hires;
  return typeof src === "string" ? src : null;
}

function cardNumberKey(sale: SaleBrowseOut): string {
  return (sale.card.number ?? sale.card.card_number ?? "").toString();
}

export function SalesClient() {
  const [q, setQ] = useState("");
  const [chip, setChip] = useState<ChipFilter>({ kind: "all" });
  const [showcaseSort, setShowcaseSort] = useState<ShowcaseSort>("recent");
  const [rows, setRows] = useState<SaleBrowseOut[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const requestId = useRef(0);

  const game = chip.kind === "game" ? chip.value : "";
  const grade = chip.kind === "grade" ? chip.value : "";
  const apiSort: ShopSort = "recent";

  const load = useCallback(
    async (offset: number, append: boolean) => {
      const id = ++requestId.current;
      setLoading(true);
      setError(null);
      try {
        const out = await getSalesBrowse({
          q: q.trim() || undefined,
          game: game || undefined,
          grade: grade || undefined,
          sort: apiSort,
          limit: PAGE_SIZE,
          offset,
        });
        if (id !== requestId.current) return;
        setRows((prev) => (append ? [...prev, ...out] : out));
        setHasMore(out.length === PAGE_SIZE);
      } catch (e) {
        if (id !== requestId.current) return;
        setError(e instanceof Error ? e.message : "Failed to load sales");
        if (!append) setRows([]);
      } finally {
        if (id === requestId.current) setLoading(false);
      }
    },
    [q, game, grade],
  );

  useEffect(() => {
    const t = setTimeout(() => void load(0, false), q ? 300 : 0);
    return () => clearTimeout(t);
  }, [load, q]);

  const displayRows = useMemo(() => {
    const copy = [...rows];
    if (showcaseSort === "alpha") {
      copy.sort((a, b) => a.card.name.localeCompare(b.card.name));
    } else if (showcaseSort === "number") {
      copy.sort((a, b) => cardNumberKey(a).localeCompare(cardNumberKey(b), undefined, { numeric: true }));
    }
    return copy;
  }, [rows, showcaseSort]);

  const chipActive = (f: ChipFilter) => {
    if (f.kind === "all") return chip.kind === "all";
    if (f.kind === "game") return chip.kind === "game" && chip.value === f.value;
    return chip.kind === "grade" && chip.value === f.value;
  };

  return (
    <div>
      <style>{`
        @keyframes cc-fade { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }
        .cc-sales { animation: cc-fade .4s ease; }
        .cc-sales-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 16px; margin-top: 26px; }
        @media (max-width: 1100px) { .cc-sales-grid { grid-template-columns: repeat(4, 1fr); } }
        @media (max-width: 860px) { .cc-sales-grid { grid-template-columns: repeat(3, 1fr); } }
        @media (max-width: 640px) { .cc-sales-grid { grid-template-columns: repeat(2, 1fr); } }
        .cc-chip { font-size: 12.5px; font-weight: 600; padding: 7px 13px; border-radius: 99px; cursor: pointer; border: 1px solid var(--border); color: var(--text2); background: var(--surface); white-space: nowrap; flex: none; font-family: var(--font-body); }
        .cc-chip[data-active="true"] { color: var(--accent-ink); background: var(--accent); border-color: var(--accent); }
        .cc-sort { font-size: 12px; font-weight: 600; padding: 6px 11px; border-radius: 8px; cursor: pointer; color: var(--text2); background: transparent; border: none; white-space: nowrap; font-family: var(--font-body); }
        .cc-sort[data-active="true"] { color: var(--accent); background: var(--surface2); }
        .cc-tile { background: var(--surface); border: 1px solid var(--border); border-radius: 11px; overflow: hidden; box-shadow: 0 1px 2px rgba(23,24,28,0.05); text-decoration: none; color: inherit; display: block; transition: border-color .15s; }
        .cc-tile:hover { border-color: var(--accent); }
      `}</style>

      <div className="cc-sales">
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: 13,
            padding: "14px 18px",
            marginTop: 18,
            boxShadow: "0 1px 2px rgba(23,24,28,0.05)",
          }}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden style={{ color: "var(--text3)", flex: "none" }}>
            <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
            <path d="m20 20-3-3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
          <input
            type="search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search 1,000,000+ cards across 25+ games…"
            style={{
              flex: 1,
              border: "none",
              outline: "none",
              background: "transparent",
              fontSize: 15,
              color: "var(--text)",
              fontFamily: "var(--font-body)",
              minWidth: 0,
            }}
          />
        </div>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 12,
            marginTop: 16,
            flexWrap: "wrap",
          }}
        >
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {FILTER_CHIPS.map((ch) => (
              <button
                key={ch.label}
                type="button"
                className="cc-chip"
                data-active={chipActive(ch.filter)}
                onClick={() => setChip(ch.filter)}
              >
                {ch.label}
              </button>
            ))}
          </div>
          <div style={{ display: "flex", gap: 6 }}>
            {SHOWCASE_SORTS.map((so) => (
              <button
                key={so.value}
                type="button"
                className="cc-sort"
                data-active={showcaseSort === so.value}
                onClick={() => setShowcaseSort(so.value)}
              >
                {so.label}
              </button>
            ))}
          </div>
        </div>

        {error && <p style={{ color: "var(--down)", fontSize: 14, marginTop: 16 }}>{error}</p>}

        <div className="cc-sales-grid">
          {displayRows.map((s, i) => {
            const img = thumb(s);
            const gradeLabel = formatGradeLabel(s.grade) || "Raw";
            return (
              <Link
                key={`${s.sold_at}-${s.card.id}-${i}`}
                href={`/card/${s.card.slug}`}
                className="cc-tile"
              >
                <div
                  style={{
                    aspectRatio: "5 / 7",
                    background:
                      "repeating-linear-gradient(135deg, var(--surface2), var(--surface2) 7px, var(--bg) 7px, var(--bg) 14px)",
                    borderBottom: "1px solid var(--border)",
                    position: "relative",
                    overflow: "hidden",
                  }}
                >
                  {img ? (
                    <Image
                      src={img}
                      alt={s.card.name}
                      fill
                      sizes="(max-width: 640px) 50vw, 20vw"
                      style={{ objectFit: "cover" }}
                    />
                  ) : null}
                  <span
                    style={{
                      position: "absolute",
                      top: 8,
                      left: 8,
                      fontSize: 10,
                      fontWeight: 700,
                      padding: "3px 7px",
                      borderRadius: 6,
                      background: "var(--surface)",
                      border: "1px solid var(--border)",
                      color: "var(--text2)",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {gradeLabel}
                  </span>
                  <span
                    style={{
                      position: "absolute",
                      top: 8,
                      right: 8,
                      fontSize: 10,
                      fontWeight: 700,
                      padding: "3px 7px",
                      borderRadius: 6,
                      background: "var(--hold-bg)",
                      color: "var(--hold)",
                      whiteSpace: "nowrap",
                      textTransform: "capitalize",
                    }}
                  >
                    {s.source}
                  </span>
                </div>
                <div style={{ padding: 12 }}>
                  <div
                    style={{
                      fontWeight: 700,
                      fontSize: 13.5,
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {s.card.name}
                  </div>
                  <div
                    style={{
                      fontSize: 11.5,
                      color: "var(--text3)",
                      marginTop: 2,
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {s.card.set_name ?? s.card.set_code ?? s.market_region}
                    {s.card.number ? ` · #${s.card.number}` : ""}
                  </div>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "baseline",
                      justifyContent: "space-between",
                      marginTop: 8,
                      gap: 8,
                    }}
                  >
                    <span
                      style={{
                        fontFamily: "var(--font-num)",
                        fontWeight: 800,
                        fontSize: 15,
                        fontVariantNumeric: "tabular-nums",
                      }}
                    >
                      {fmtNative(s.price, s.currency)}
                    </span>
                    <span
                      style={{
                        fontSize: 11,
                        fontWeight: 600,
                        color: "var(--text3)",
                        whiteSpace: "nowrap",
                      }}
                    >
                      Sold
                    </span>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>

        {!loading && displayRows.length === 0 && !error && (
          <p style={{ textAlign: "center", fontSize: 14, color: "var(--text3)", marginTop: 40 }}>
            No sales match. Try clearing filters. Sold comps require completed/sold data from
            eBay/Cardmarket/paid sources.
          </p>
        )}

        <div style={{ display: "flex", justifyContent: "center", marginTop: 28 }}>
          {loading ? (
            <p style={{ fontSize: 14, color: "var(--text3)" }}>Loading…</p>
          ) : hasMore ? (
            <button
              type="button"
              onClick={() => void load(rows.length, true)}
              style={{
                fontSize: 13,
                fontWeight: 600,
                padding: "10px 16px",
                borderRadius: 10,
                background: "transparent",
                border: "1px solid var(--border)",
                color: "var(--text)",
                cursor: "pointer",
                fontFamily: "var(--font-body)",
              }}
            >
              Load more
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}
