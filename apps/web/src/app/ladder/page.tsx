import type { Metadata } from "next";
import { LadderClient } from "./ladder-client";

export const metadata: Metadata = {
  title: "Card Price Guide — TCG Scan",
  description:
    "Browse the market ladder: last sold prices, 30-day sales volume, and 1-month price changes across every tracked card.",
};

export default function LadderPage() {
  return (
    <main className="mx-auto max-w-5xl px-4 py-10">
      <h1 className="text-2xl font-bold">Ladder</h1>
      <p className="mt-2 text-sm text-zinc-600">
        The market at a glance — last sold prices, monthly movement, and sales volume across
        every card we track. Click any row for full comps and charts.
      </p>
      <div className="mt-8">
        <LadderClient />
      </div>
    </main>
  );
}
