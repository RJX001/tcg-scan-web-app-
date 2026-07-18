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
  const stroke = up ? "#1E9A6B" : "#D6444B";

  return (
    <div
      className="rounded-[11px] border p-4 shadow-[0_1px_2px_rgba(23,24,28,0.05)]"
      style={{
        background: "#FFFFFF",
        borderColor: "#E4E1D8",
        fontFamily: "'Hanken Grotesk', system-ui, sans-serif",
      }}
    >
      <div className="flex items-baseline justify-between">
        <div>
          <p
            className="text-[11px] font-bold uppercase tracking-[0.08em]"
            style={{ color: "#84878F" }}
          >
            Composite index · 90d
          </p>
          <p className="font-semibold" style={{ color: "#17181C" }}>
            {index.name}
          </p>
        </div>
        <span
          className="rounded-md px-1.5 py-0.5 text-sm font-semibold tabular-nums"
          style={{
            background: up ? "rgba(30,154,107,0.13)" : "rgba(214,68,75,0.13)",
            color: stroke,
            fontFamily: "'IBM Plex Mono', monospace",
          }}
        >
          {up ? "+" : ""}
          {change.toFixed(2)}%
        </span>
      </div>
      <div className="mt-3 h-40 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E4E1D8" />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 11, fill: "#84878F" }}
              interval="preserveStartEnd"
              axisLine={{ stroke: "#E4E1D8" }}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 11, fill: "#84878F" }}
              domain={["auto", "auto"]}
              tickFormatter={(v: number) => v.toFixed(0)}
              width={44}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              contentStyle={{
                background: "#1E2128",
                border: "1px solid #2A2E37",
                borderRadius: 8,
                color: "#F6F7F9",
                fontSize: 12,
              }}
              formatter={(value: number, _name, item) => [
                `${value.toFixed(2)} (${(item?.payload as { constituents?: number })?.constituents ?? "?"} cards)`,
                "Index",
              ]}
            />
            <Line
              type="monotone"
              dataKey="index_value"
              stroke={stroke}
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-2 text-xs" style={{ color: "#84878F" }}>
        Equal-weighted, rebased to 100 at window start, like the CL50 — based on daily median
        sale prices.
      </p>
    </div>
  );
}
