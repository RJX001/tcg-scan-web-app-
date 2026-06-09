"use client";

import {
  MARKET_REGION_FILTERS,
  type MarketRegionFilter,
} from "@/lib/market-regions";

type Props = {
  value: MarketRegionFilter;
  onChange: (value: MarketRegionFilter) => void;
  uppercase?: boolean;
};

export function RegionFilterBar({ value, onChange, uppercase = false }: Props) {
  return (
    <div className={`flex flex-wrap gap-2 ${uppercase ? "uppercase" : ""}`}>
      {MARKET_REGION_FILTERS.map((f) => (
        <button
          key={f.id}
          type="button"
          onClick={() => onChange(f.id)}
          className={`rounded-full px-3 py-1 text-xs ${
            value === f.id ? "bg-blue-600 text-white" : "bg-zinc-100 text-zinc-700"
          }`}
        >
          {f.label}
        </button>
      ))}
    </div>
  );
}
