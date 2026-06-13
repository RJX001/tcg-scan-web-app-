"use client";

import { useEffect, useState } from "react";
import type { MarketIndexOut } from "@tcgscan/sdk-ts";
import { getMarketIndex } from "@tcgscan/sdk-ts";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export function IndexChart({ game }: { game: string }) {
  const [index, setIndex] = useState<MarketIndexOut | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setError(false);
    getMarketIndex({ game: game || undefined, days: 90 })
      .then((out) => {
        if (!cancelled) setIndex(out);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });
    return () => {
      cancelled = true;
    };
  }, [game]);

  if (error || !index || index.points.length < 2) return null;

  const data = index.points.map((p) => ({
    ...p,
    label: new Date(p.day).toLocaleDateString(undefined, { month: "short", day: "numeric" }),
  }));
  const change = index.change_pct ?? 0;
  const up = change >= 0;

  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-4">
      <div className="flex items-baseline justify-between">
        <div>
          <p className="text-xs uppercase tracking-wide text-zinc-500">Composite index · 90d</p>
          <p className="font-semibold">{index.name}</p>
        </div>
        <span
          className={`rounded px-1.5 py-0.5 text-sm font-semibold ${
            up ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
          }`}
        >
          {up ? "+" : ""}
          {change.toFixed(2)}%
        </span>
      </div>
      <div className="mt-3 h-40 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" />
            <XAxis dataKey="label" tick={{ fontSize: 11 }} interval="preserveStartEnd" />
            <YAxis
              tick={{ fontSize: 11 }}
              domain={["auto", "auto"]}
              tickFormatter={(v: number) => v.toFixed(0)}
              width={44}
            />
            <Tooltip
              formatter={(value: number, _name, item) => [
                `${value.toFixed(2)} (${(item?.payload as { constituents?: number })?.constituents ?? "?"} cards)`,
                "Index",
              ]}
            />
            <Line
              type="monotone"
              dataKey="index_value"
              stroke={up ? "#16a34a" : "#dc2626"}
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-2 text-xs text-zinc-400">
        Equal-weighted, rebased to 100 at window start, like the CL50 — based on daily median
        sale prices.
      </p>
    </div>
  );
}
