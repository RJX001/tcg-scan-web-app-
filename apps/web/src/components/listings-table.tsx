"use client";

import { useMemo, useState } from "react";
import type { ListingOut } from "@tcgscan/sdk-ts";
import { SalesTableFilters } from "@/components/sales-table-filters";
import { matchesGradeFilter, type GradeCompanyFilter } from "@/lib/grade-filters";
import {
  matchesMarketRegionFilter,
  type MarketRegionFilter,
} from "@/lib/market-regions";
import { formatGradeLabel, formatSourceLabel } from "@/lib/sales-display";

/** Listings carry their source currency (eBay USD, Cardmarket EUR, …) — show it honestly. */
function fmtNative(n: number, currency: string) {
  try {
    return new Intl.NumberFormat(undefined, { style: "currency", currency }).format(n);
  } catch {
    return `${currency} ${n.toFixed(2)}`;
  }
}

type Props = {
  listings: ListingOut[];
};

export function ListingsTable({ listings }: Props) {
  const sources = useMemo(() => {
    const set = new Set(listings.map((l) => l.source));
    return Array.from(set);
  }, [listings]);

  const [source, setSource] = useState("all");
  const [gradeFilter, setGradeFilter] = useState<GradeCompanyFilter>("all");
  const [gradeSub, setGradeSub] = useState("");
  const [regionFilter, setRegionFilter] = useState<MarketRegionFilter>("all");

  const availableGrades = useMemo(() => listings.map((l) => l.grade), [listings]);

  const filtered = useMemo(
    () =>
      listings.filter(
        (l) =>
          (source === "all" || l.source === source) &&
          matchesGradeFilter(l.grade, gradeFilter, gradeSub) &&
          matchesMarketRegionFilter(l, regionFilter),
      ),
    [listings, source, gradeFilter, gradeSub, regionFilter],
  );

  if (listings.length === 0) {
    return (
      <p className="text-sm text-zinc-600">No active listings in the database yet.</p>
    );
  }

  return (
    <div className="uppercase">
      <SalesTableFilters
        sources={sources}
        source={source}
        onSourceChange={setSource}
        gradeFilter={gradeFilter}
        gradeSub={gradeSub}
        onGradeFilterChange={setGradeFilter}
        onGradeSubChange={setGradeSub}
        availableGrades={availableGrades}
        regionFilter={regionFilter}
        onRegionFilterChange={setRegionFilter}
      />
      {filtered.length === 0 ? (
        <p className="mt-3 text-sm normal-case text-zinc-600">No listings match the selected filters.</p>
      ) : (
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b text-zinc-500">
                <th className="py-2 pr-4">PRICE</th>
                <th className="py-2 pr-4">GRADE</th>
                <th className="py-2 pr-4">SOURCE</th>
                <th className="py-2">MARKET</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((row, i) => (
                <tr key={`${row.listed_at}-${i}`} className="border-b border-zinc-100">
                  <td className="py-2 pr-4 font-medium normal-case">
                    {row.listing_url ? (
                      <a
                        href={row.listing_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline"
                      >
                        {fmtNative(row.price, row.currency)}
                      </a>
                    ) : (
                      fmtNative(row.price, row.currency)
                    )}
                  </td>
                  <td className="py-2 pr-4">{formatGradeLabel(row.grade)}</td>
                  <td className="py-2 pr-4">{formatSourceLabel(row.source)}</td>
                  <td className="py-2">{row.market_region.toUpperCase()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
