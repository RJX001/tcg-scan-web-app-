"use client";

import { useEffect, useState } from "react";
import type { IndexSummaryOut } from "@tcgscan/sdk-ts";
import { getIndexes } from "@tcgscan/sdk-ts";
import { IndexChart } from "../ladder/index-chart";

const PERIODS = [
  { label: "1W", days: 7 },
  { label: "1M", days: 30 },
  { label: "3M", days: 90 },
  { label: "1Y", days: 365 },
];

function ChangeBadge({ pct }: { pct: number | null | undefined }) {
  if (pct == null) return <span className="text-sm text-zinc-400">—</span>;
  const up = pct >= 0;
  return (
    <span className={`text-sm font-bold ${up ? "text-green-600" : "text-red-600"}`}>
      {up ? "+" : ""}
      {pct.toFixed(2)}%
    </span>
  );
}

export function IndexesClient() {
  const [days, setDays] = useState(7);
  const [rows, setRows] = useState<IndexSummaryOut[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getIndexes(days)
      .then((out) => {
        if (!cancelled) setRows(out);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load indexes");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [days]);

  const periodLabel = PERIODS.find((p) => p.days === days)?.label ?? `${days}d`;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex gap-2">
        {PERIODS.map((p) => (
          <button
            key={p.days}
            type="button"
            onClick={() => setDays(p.days)}
            className={`rounded-full border px-3 py-1 text-xs font-medium ${
              days === p.days
                ? "border-blue-700 bg-blue-700 text-white"
                : "border-zinc-300 bg-white text-zinc-600 hover:border-zinc-400"
            }`}
          >
            {p.label}
          </button>
        ))}
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <ul className="divide-y divide-zinc-100 overflow-hidden rounded-xl border border-zinc-200 bg-white">
        {rows.map((idx) => (
          <li key={idx.key}>
            <button
              type="button"
              onClick={() => setExpanded((cur) => (cur === idx.key ? null : idx.key))}
              className="flex w-full items-center justify-between px-4 py-4 text-left hover:bg-zinc-50"
              aria-expanded={expanded === idx.key}
            >
              <div>
                <p className="font-semibold">{idx.name}</p>
                <p className="text-xs text-zinc-500">
                  {idx.constituents} card{idx.constituents === 1 ? "" : "s"} · level{" "}
                  {idx.latest_value?.toFixed(2) ?? "—"}
                </p>
              </div>
              <div className="text-right">
                <p className="text-[11px] uppercase tracking-wide text-zinc-400">
                  {periodLabel} change
                </p>
                <ChangeBadge pct={idx.change_pct} />
              </div>
            </button>
            {expanded === idx.key && (
              <div className="border-t border-zinc-100 p-4">
                <IndexChart game={idx.key === "all" ? "" : idx.key} />
              </div>
            )}
          </li>
        ))}
        {!loading && rows.length === 0 && !error && (
          <li className="px-4 py-10 text-center text-sm text-zinc-500">
            No index data yet — run <code className="rounded bg-zinc-100 px-1">pnpm db:seed</code>.
          </li>
        )}
      </ul>
      {loading && <p className="text-center text-sm text-zinc-500">Loading…</p>}
    </div>
  );
}
