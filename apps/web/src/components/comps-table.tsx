"use client";

import { useMemo, useState } from "react";
import type { CompOut } from "@tcgscan/sdk-ts";
import { SalesTableFilters } from "@/components/sales-table-filters";
import { SoldAtCell } from "@/components/sold-at-cell";
import { matchesGradeFilter, type GradeCompanyFilter } from "@/lib/grade-filters";
import {
  matchesMarketRegionFilter,
  type MarketRegionFilter,
} from "@/lib/market-regions";
import { formatGradeLabel, formatSourceLabel } from "@/lib/sales-display";

/** Comps carry their source currency (eBay USD, Cardmarket EUR, …) — show it honestly. */
function fmtNative(n: number, currency: string) {
  try {
    return new Intl.NumberFormat(undefined, { style: "currency", currency }).format(n);
  } catch {
    return `${currency} ${n.toFixed(2)}`;
  }
}

type Props = {
  comps: CompOut[];
  /** `panel` = dark Daylight table surface used on card detail. */
  tone?: "light" | "panel";
};

export function CompsTable({ comps, tone = "light" }: Props) {
  const panel = tone === "panel";
  const sources = useMemo(() => {
    const set = new Set(comps.map((c) => c.source));
    return Array.from(set);
  }, [comps]);

  const [source, setSource] = useState("all");
  const [gradeFilter, setGradeFilter] = useState<GradeCompanyFilter>("all");
  const [gradeSub, setGradeSub] = useState("");
  const [regionFilter, setRegionFilter] = useState<MarketRegionFilter>("all");

  const availableGrades = useMemo(() => comps.map((c) => c.grade), [comps]);

  const filtered = useMemo(
    () =>
      comps.filter(
        (c) =>
          (source === "all" || c.source === source) &&
          matchesGradeFilter(c.grade, gradeFilter, gradeSub) &&
          matchesMarketRegionFilter(c, regionFilter),
      ),
    [comps, source, gradeFilter, gradeSub, regionFilter],
  );

  if (comps.length === 0) {
    return (
      <p className={`text-sm ${panel ? "text-[#BAC0CB]" : "text-zinc-600"}`}>
        No sold comps yet for this window.
      </p>
    );
  }

  const head = panel ? "text-[#8C93A1]" : "text-zinc-500";
  const rowBorder = panel ? "border-[#2A2E37]" : "border-zinc-100";
  const link = panel ? "text-[#E0B94A] hover:underline" : "text-blue-600 hover:underline";
  const gradeChip = panel
    ? "rounded-md border border-[#2A2E37] bg-[#252932] px-2 py-0.5 text-[11px] font-bold text-[#E0B94A]"
    : "";

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
        <p className={`mt-3 text-sm normal-case ${panel ? "text-[#BAC0CB]" : "text-zinc-600"}`}>
          No comps match the selected filters.
        </p>
      ) : (
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className={`border-b ${head} ${panel ? "border-[#2A2E37]" : ""}`}>
                <th className="py-2 pr-4">SOLD</th>
                <th className="py-2 pr-4">PRICE</th>
                <th className="py-2 pr-4">GRADE</th>
                <th className="py-2 pr-4">SOURCE</th>
                <th className="py-2">MARKET</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((c, i) => (
                <tr key={`${c.sold_at}-${i}`} className={`border-b ${rowBorder}`}>
                  <SoldAtCell iso={c.sold_at} className="py-2 pr-4 whitespace-nowrap normal-case" />
                  <td className="py-2 pr-4 font-medium normal-case">
                    {c.listing_url ? (
                      <a
                        href={c.listing_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={link}
                      >
                        {fmtNative(c.price, c.currency)}
                      </a>
                    ) : (
                      fmtNative(c.price, c.currency)
                    )}
                  </td>
                  <td className="py-2 pr-4">
                    {gradeChip ? (
                      <span className={gradeChip}>{formatGradeLabel(c.grade)}</span>
                    ) : (
                      formatGradeLabel(c.grade)
                    )}
                  </td>
                  <td className="py-2 pr-4">{formatSourceLabel(c.source)}</td>
                  <td className="py-2">{c.market_region.toUpperCase()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
