import type { Metadata } from "next";

import { SalesClient } from "./sales-client";

export const metadata: Metadata = {
  title: "Sales — CardChart",
  description:
    "Browse recent sold comps across eBay, TCGPlayer, Cardmarket, and more — filter by grade, platform, and date.",
};

export default function SalesPage() {
  return (
    <main className="mx-auto max-w-[1200px] px-6 pb-10">
      <div className="pt-10">
        <h1 className="font-display text-[32px] font-extrabold tracking-[-0.02em] text-[var(--text)]">
          Sales
        </h1>
        <p className="mt-1 text-[14.5px] text-[var(--text2)]">
          A visual browse of recent sold comps. Tap any card for prices and history.
        </p>
      </div>
      <SalesClient />
    </main>
  );
}
