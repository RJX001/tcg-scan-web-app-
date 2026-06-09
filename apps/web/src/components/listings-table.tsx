"use client";

import { useMemo, useState } from "react";
import type { ListingOut } from "@tcgscan/sdk-ts";
import { GradeFilterBar } from "@/components/grade-filter-bar";
import { RegionFilterBar } from "@/components/region-filter-bar";
import {
  matchesGradeCompanyFilter,
  type GradeCompanyFilter,
} from "@/lib/grade-filters";
import {
  matchesMarketRegionFilter,
  type MarketRegionFilter,
} from "@/lib/market-regions";

function fmtUsd(n: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n);
}

type Props = {
  listings: ListingOut[];
};

export function ListingsTable({ listings }: Props) {
  const sources = useMemo(() => {
    const set = new Set(listings.map((l) => l.source));
    return ["all", ...Array.from(set).sort()];
  }, [listings]);

  const [source, setSource] = useState("all");
  const [gradeFilter, setGradeFilter] = useState<GradeCompanyFilter>("all");
  const [regionFilter, setRegionFilter] = useState<MarketRegionFilter>("all");

  const filtered = useMemo(
    () =>
      listings.filter(
        (l) =>
          (source === "all" || l.source === source) &&
          matchesGradeCompanyFilter(l.grade, gradeFilter) &&
          matchesMarketRegionFilter(l, regionFilter),
      ),
    [listings, source, gradeFilter, regionFilter],
  );

  if (listings.length === 0) {
    return (
      <p className="text-sm text-zinc-600">No active listings in the database yet.</p>
    );
  }

  return (
    <div>
      <div className="mb-2 space-y-2">
        <RegionFilterBar value={regionFilter} onChange={setRegionFilter} />
        <GradeFilterBar value={gradeFilter} onChange={setGradeFilter} />
        <div className="flex flex-wrap gap-2">
          {sources.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => setSource(s)}
              className={`rounded-full px-3 py-1 text-xs capitalize ${
                source === s ? "bg-zinc-900 text-white" : "bg-zinc-100 text-zinc-700"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>
      {filtered.length === 0 ? (
        <p className="text-sm text-zinc-600">No listings match the selected filters.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b text-zinc-500">
                <th className="py-2 pr-4">Price</th>
                <th className="py-2 pr-4">Grade</th>
                <th className="py-2 pr-4">Source</th>
                <th className="py-2">Market</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((row, i) => (
                <tr key={`${row.listed_at}-${i}`} className="border-b border-zinc-100">
                  <td className="py-2 pr-4 font-medium">
                    {row.listing_url ? (
                      <a
                        href={row.listing_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline"
                      >
                        {fmtUsd(row.price)}
                      </a>
                    ) : (
                      fmtUsd(row.price)
                    )}
                  </td>
                  <td className="py-2 pr-4">{row.grade ?? "raw"}</td>
                  <td className="py-2 pr-4">{row.source}</td>
                  <td className="py-2 uppercase">{row.market_region}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
