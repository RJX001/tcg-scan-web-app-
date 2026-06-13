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

type Props = { data: ChartPoint[] };

export function PriceChart({ data }: Props) {
  const { fmt } = useCurrency();
  if (data.length === 0) {
    return (
      <p className="text-sm text-zinc-500">
        No chart data yet — run <code className="rounded bg-zinc-100 px-1">pnpm rollup:daily</code> or{" "}
        <code className="rounded bg-zinc-100 px-1">pnpm db:seed</code>.
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
          <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" />
          <XAxis dataKey="label" tick={{ fontSize: 11 }} interval="preserveStartEnd" />
          <YAxis
            tick={{ fontSize: 11 }}
            tickFormatter={(v: number) => fmt(v)}
            width={64}
          />
          <Tooltip formatter={(value: number) => [fmt(value), "Median"]} />
          <Line type="monotone" dataKey="median_usd" stroke="#2563eb" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
