"use client";

import { useMemo, useState } from "react";
import type { CompOut } from "@tcgscan/sdk-ts";

function fmtUsd(n: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n);
}

type Props = {
  comps: CompOut[];
};

export function CompsTable({ comps }: Props) {
  const sources = useMemo(() => {
    const set = new Set(comps.map((c) => c.source));
    return ["all", ...Array.from(set).sort()];
  }, [comps]);

  const [source, setSource] = useState("all");

  const filtered =
    source === "all" ? comps : comps.filter((c) => c.source === source);

  if (comps.length === 0) {
    return (
      <p className="text-sm text-zinc-600">
        No comps yet. Run <code className="rounded bg-zinc-100 px-1">pnpm db:seed</code>.
      </p>
    );
  }

  return (
    <div>
      <div className="mb-3 flex flex-wrap gap-2">
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
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b text-zinc-500">
              <th className="py-2 pr-4">Date</th>
              <th className="py-2 pr-4">Price</th>
              <th className="py-2 pr-4">Grade</th>
              <th className="py-2">Source</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((c, i) => (
              <tr key={`${c.sold_at}-${i}`} className="border-b border-zinc-100">
                <td className="py-2 pr-4">{new Date(c.sold_at).toLocaleDateString()}</td>
                <td className="py-2 pr-4 font-medium">
                  {c.listing_url ? (
                    <a
                      href={c.listing_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:underline"
                    >
                      {fmtUsd(c.price)}
                    </a>
                  ) : (
                    fmtUsd(c.price)
                  )}
                </td>
                <td className="py-2 pr-4">{c.grade ?? "raw"}</td>
                <td className="py-2">{c.source}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
