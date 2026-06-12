import type { Metadata } from "next";
import { ShopClient } from "./shop-client";

export const metadata: Metadata = {
  title: "Shop — TCG Scan",
  description:
    "Browse live marketplace listings across eBay, TCGPlayer, and Cardmarket with price, platform, and grade filters.",
};

export default function ShopPage() {
  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <h1 className="text-2xl font-bold tracking-tight">Shop</h1>
      <p className="mt-1 text-sm text-zinc-600">
        Live listings across every marketplace we track. Tap a listing to open it, or the card
        name for full comps.
      </p>
      <div className="mt-6">
        <ShopClient />
      </div>
    </main>
  );
}
