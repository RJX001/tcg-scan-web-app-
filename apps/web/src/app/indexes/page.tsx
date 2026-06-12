import type { Metadata } from "next";
import { IndexesClient } from "./indexes-client";

export const metadata: Metadata = {
  title: "Indexes — TCG Scan",
  description:
    "Composite market indexes for every game we track — equal-weighted, CL50-style, with weekly change.",
};

export default function IndexesPage() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="text-2xl font-bold tracking-tight">Indexes</h1>
      <p className="mt-1 text-sm text-zinc-600">
        Equal-weighted composites rebased to 100 at window start. Tap an index to expand its
        chart.
      </p>
      <div className="mt-6">
        <IndexesClient />
      </div>
    </main>
  );
}
