"use client";

import type { ChartPoint } from "@tcgscan/sdk-ts";
import { useCurrency } from "@/lib/currency";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type Props = {
  data: ChartPoint[];
  /** Stroke colour — Daylight gold by default on card detail. */
  accent?: string;
};

export function PriceChart({ data, accent = "#B6862E" }: Props) {
  const { fmt } = useCurrency();
  if (data.length === 0) {
    return (
      <p className="text-sm text-[#84878F]">
        No chart data yet — sold comps will populate this once marketplace sources connect.
      </p>
    );
  }

  const formatted = data.map((d) => ({
    ...d,
    label: new Date(d.day).toLocaleDateString(undefined, { month: "short", day: "numeric" }),
  }));

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={formatted} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#ECE9E0" />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 11, fill: "#84878F" }}
            interval="preserveStartEnd"
            axisLine={{ stroke: "#E4E1D8" }}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 11, fill: "#84878F" }}
            tickFormatter={(v: number) => fmt(v)}
            width={64}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip formatter={(value: number) => [fmt(value), "Median"]} />
          <Line
            type="monotone"
            dataKey="median_usd"
            stroke={accent}
            strokeWidth={2.4}
            dot={false}
            activeDot={{ r: 4, stroke: accent, strokeWidth: 2, fill: "#FFFFFF" }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
