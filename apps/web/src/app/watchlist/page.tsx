import type { Metadata } from "next";
import { WatchlistClient } from "./watchlist-client";

export const metadata: Metadata = {
  title: "Watchlist — TCG Scan",
};

export default function WatchlistPage() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="text-2xl font-bold tracking-tight">Watchlist</h1>
      <p className="mt-1 text-sm text-zinc-600">
        Cards you&apos;re tracking without owning. Add cards from any card page.
      </p>
      <div className="mt-6">
        <WatchlistClient />
      </div>
    </main>
  );
}
