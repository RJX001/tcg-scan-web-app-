import type { Metadata } from "next";

import { ListingsClient } from "./listings-client";

export const metadata: Metadata = {
  title: "Listings — CardChart",
  description:
    "Browse live marketplace listings across eBay, TCGPlayer, and Cardmarket with price and sort filters.",
};

export default function ListingsPage() {
  return (
    <main className="mx-auto max-w-[1200px] px-6 pb-10">
      <div className="pt-10 pb-2">
        <h1 className="font-display text-[32px] font-extrabold tracking-[-0.02em] text-[var(--text)]">
          Listings
        </h1>
        <p className="mt-1 text-[14.5px] text-[var(--text2)]">
          Live listings across every marketplace we track. Tap a listing to open it, or the card
          name for full comps.
        </p>
      </div>
      <ListingsClient />
    </main>
  );
}
