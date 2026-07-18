"use client";

import Image from "next/image";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import type { ShopListingOut, ShopSort } from "@tcgscan/sdk-ts";
import { getShopListings } from "@tcgscan/sdk-ts";
import { useCurrency } from "@/lib/currency";

const PAGE_SIZE = 24;

const SORTS: { value: ShopSort; label: string }[] = [
  { value: "recent", label: "Recently added" },
  { value: "price_asc", label: "Price: low to high" },
  { value: "price_desc", label: "Price: high to low" },
];

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

function listingSub(listing: ShopListingOut): string {
  const parts: string[] = [];
  if (listing.card?.set_name ?? listing.card?.set_code) {
    parts.push(String(listing.card?.set_name ?? listing.card?.set_code));
  }
  if (listing.card?.number) parts.push(`#${listing.card.number}`);
  if (parts.length === 0) {
    return listing.title && listing.card?.name ? listing.title : "Active listing";
  }
  return parts.join(" · ");
}

function listingSeller(listing: ShopListingOut): string {
  if (listing.grade) return listing.grade;
  return "Marketplace";
}

export function ListingsClient() {
  const [sort, setSort] = useState<ShopSort>("recent");
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
    [sort],
  );

  useEffect(() => {
    void load(0, false);
  }, [load]);

  return (
    <div
      style={{
        ["--bg" as string]: "#F7F6F2",
        ["--surface" as string]: "#FFFFFF",
        ["--border" as string]: "#E4E1D8",
        ["--text" as string]: "#17181C",
        ["--text2" as string]: "#5B5F68",
        ["--text3" as string]: "#84878F",
        ["--accent" as string]: "#B6862E",
        ["--accent-ink" as string]: "#1A1408",
        ["--panel" as string]: "#1E2128",
        ["--panel2" as string]: "#252932",
        ["--panel-border" as string]: "#2A2E37",
        ["--panel-text" as string]: "#F6F7F9",
        ["--panel-text2" as string]: "#BAC0CB",
        ["--panel-text3" as string]: "#8C93A1",
        ["--panel-gold" as string]: "#E0B94A",
        ["--font-body" as string]: "'Hanken Grotesk', system-ui, sans-serif",
        ["--font-num" as string]: "'IBM Plex Mono', ui-monospace, monospace",
        fontFamily: "var(--font-body)",
        color: "var(--text)",
      }}
    >
      <style>{`
        @keyframes cc-fade { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }
        .cc-listings { animation: cc-fade .4s ease; }
        .cc-chip { font-size: 12.5px; font-weight: 600; padding: 7px 13px; border-radius: 99px; cursor: pointer; border: 1px solid var(--border); color: var(--text2); background: var(--surface); white-space: nowrap; font-family: var(--font-body); }
        .cc-chip[data-active="true"] { color: var(--accent-ink); background: var(--accent); border-color: var(--accent); }
        .cc-list-row { display: grid; grid-template-columns: 48px 1.8fr 1fr 1fr 1fr auto; gap: 12px; align-items: center; padding: 12px 18px; border-bottom: 1px solid var(--panel-border); }
        @media (max-width: 760px) {
          .cc-list-head { display: none !important; }
          .cc-list-row { grid-template-columns: 48px 1fr auto; gap: 10px; }
          .cc-list-hide-sm { display: none !important; }
        }
      `}</style>

      <div className="cc-listings">
        <div style={{ display: "flex", gap: 6, marginTop: 16, flexWrap: "wrap" }}>
          {SORTS.map((s) => (
            <button
              key={s.value}
              type="button"
              className="cc-chip"
              data-active={sort === s.value}
              onClick={() => setSort(s.value)}
            >
              {s.label}
            </button>
          ))}
        </div>

        {error && <p style={{ color: "#D6444B", fontSize: 14, marginTop: 16 }}>{error}</p>}

        <div
          style={{
            background: "var(--panel)",
            border: "1px solid var(--panel-border)",
            borderRadius: 18,
            overflow: "hidden",
            marginTop: 16,
            boxShadow: "0 1px 2px rgba(23,24,28,0.05)",
            color: "var(--panel-text)",
          }}
        >
          <div
            className="cc-list-head"
            style={{
              display: "grid",
              gridTemplateColumns: "48px 1.8fr 1fr 1fr 1fr auto",
              gap: 12,
              padding: "12px 18px",
              fontSize: 10.5,
              letterSpacing: "0.06em",
              textTransform: "uppercase",
              color: "var(--panel-text3)",
              fontWeight: 700,
              borderBottom: "1px solid var(--panel-border)",
            }}
          >
            <div />
            <div>Listing</div>
            <div>Seller</div>
            <div>Source</div>
            <div>Price</div>
            <div />
          </div>

          {rows.map((l, i) => {
            const img = thumb(l);
            const title = listingTitle(l);
            const sub = listingSub(l);
            return (
              <div key={`${l.listing_url ?? l.title ?? i}`} className="cc-list-row">
                <div
                  style={{
                    width: 40,
                    height: 40,
                    borderRadius: 7,
                    background: "var(--panel2)",
                    border: "1px solid var(--panel-border)",
                    overflow: "hidden",
                    position: "relative",
                    flex: "none",
                  }}
                >
                  {img ? (
                    <Image src={img} alt={title} fill sizes="40px" style={{ objectFit: "cover" }} />
                  ) : null}
                </div>
                <div style={{ minWidth: 0 }}>
                  {l.card?.slug ? (
                    <Link
                      href={`/card/${l.card.slug}`}
                      style={{
                        fontWeight: 600,
                        fontSize: 14,
                        color: "var(--panel-text)",
                        textDecoration: "none",
                        display: "block",
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                      }}
                    >
                      {title}
                    </Link>
                  ) : (
                    <div
                      style={{
                        fontWeight: 600,
                        fontSize: 14,
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                      }}
                    >
                      {title}
                    </div>
                  )}
                  <div
                    style={{
                      fontSize: 11.5,
                      color: "var(--panel-text3)",
                      marginTop: 2,
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {sub}
                  </div>
                </div>
                <div className="cc-list-hide-sm" style={{ color: "var(--panel-text2)", fontSize: 13 }}>
                  {listingSeller(l)}
                </div>
                <div className="cc-list-hide-sm" style={{ color: "var(--panel-text2)", fontSize: 13 }}>
                  {l.source}
                </div>
                <div
                  style={{
                    fontWeight: 700,
                    fontFamily: "var(--font-num)",
                    fontVariantNumeric: "tabular-nums",
                    fontSize: 14,
                  }}
                >
                  {fmtMoney(l.price_usd ?? l.price)}
                </div>
                <div>
                  {l.listing_url ? (
                    <a
                      href={l.listing_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        fontSize: 12,
                        fontWeight: 700,
                        padding: "7px 13px",
                        borderRadius: 8,
                        background: "var(--accent)",
                        color: "var(--accent-ink)",
                        textDecoration: "none",
                        whiteSpace: "nowrap",
                        display: "inline-block",
                      }}
                    >
                      View
                    </a>
                  ) : l.card?.slug ? (
                    <Link
                      href={`/card/${l.card.slug}`}
                      style={{
                        fontSize: 12,
                        fontWeight: 700,
                        padding: "7px 13px",
                        borderRadius: 8,
                        background: "var(--accent)",
                        color: "var(--accent-ink)",
                        textDecoration: "none",
                        whiteSpace: "nowrap",
                        display: "inline-block",
                      }}
                    >
                      View
                    </Link>
                  ) : null}
                </div>
              </div>
            );
          })}

          {!loading && rows.length === 0 && !error && (
            <div style={{ padding: "40px 18px", textAlign: "center", fontSize: 14, color: "var(--panel-text3)" }}>
              Live eBay listings are ready after eBay ingest.{" "}
              <Link href="/cards" style={{ color: "var(--panel-gold)", fontWeight: 600 }}>
                Catalogue search
              </Link>{" "}
              is available now.
            </div>
          )}
        </div>

        <div style={{ display: "flex", justifyContent: "center", marginTop: 24 }}>
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

/** @deprecated Prefer ListingsClient — kept for shop route compatibility */
export const ShopClient = ListingsClient;
