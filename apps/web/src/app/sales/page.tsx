import type { Metadata } from "next";
import { SalesClient } from "./sales-client";

export const metadata: Metadata = {
  title: "Sales — TCG Scan",
  description:
    "Browse recent sold comps across eBay, TCGPlayer, Cardmarket, and more — filter by grade, platform, and date.",
};

export default function SalesPage() {
  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <h1 className="text-2xl font-bold tracking-tight">Sales</h1>
      <p className="mt-1 text-sm text-zinc-600">
        Recent sold comps across every marketplace we track. Filter by PSA, Beckett, CGC, and more.
      </p>
      <div className="mt-6">
        <SalesClient />
      </div>
    </main>
  );
}
