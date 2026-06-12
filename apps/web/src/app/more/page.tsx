import type { Metadata } from "next";
import Link from "next/link";
import { CurrencySelect } from "@/lib/currency";

export const metadata: Metadata = {
  title: "More — TCG Scan",
};

type Item = {
  href: string;
  label: string;
  description: string;
  pro?: boolean;
};

const ITEMS: Item[] = [
  { href: "/sales", label: "Sales", description: "Global sold-comps feed with grade & date filters" },
  { href: "/indexes", label: "Indexes", description: "Composite market indexes by game" },
  { href: "/portfolio", label: "Collection", description: "Your cards, value, and CSV export" },
  { href: "/watchlist", label: "Watchlist", description: "Track cards you don't own", pro: true },
  { href: "/alerts", label: "Price alerts", description: "Get notified on price moves", pro: true },
  { href: "/digest", label: "Daily brief", description: "AI summary of your market", pro: true },
  { href: "/search", label: "Price check", description: "Look up any card by name or photo" },
  { href: "/showcase", label: "Showcase", description: "Browse card art across the catalog" },
  { href: "/ladder", label: "Saved searches", description: "Your saved ladder filters", pro: true },
  { href: "/account", label: "Settings", description: "Account, tier, and billing" },
];

function ProBadge() {
  return (
    <span className="rounded bg-blue-700 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white">
      Pro
    </span>
  );
}

export default function MorePage() {
  return (
    <main className="mx-auto max-w-2xl px-4 py-8">
      <h1 className="text-2xl font-bold tracking-tight">More</h1>
      <div className="mt-6 flex items-center justify-between rounded-xl border border-zinc-200 bg-white px-4 py-4">
        <div>
          <p className="font-semibold">Display currency</p>
          <p className="text-xs text-zinc-500">
            Prices convert with daily ECB rates — auto-detected from your locale
          </p>
        </div>
        <CurrencySelect />
      </div>
      <ul className="mt-4 divide-y divide-zinc-100 overflow-hidden rounded-xl border border-zinc-200 bg-white">
        {ITEMS.map((item) => (
          <li key={item.label}>
            <Link
              href={item.href}
              className="flex items-center justify-between gap-3 px-4 py-4 hover:bg-zinc-50"
            >
              <div>
                <p className="flex items-center gap-2 font-semibold">
                  {item.label}
                  {item.pro && <ProBadge />}
                </p>
                <p className="text-xs text-zinc-500">{item.description}</p>
              </div>
              <span className="text-zinc-300">›</span>
            </Link>
          </li>
        ))}
      </ul>
      <div className="mt-6 rounded-xl border border-blue-200 bg-blue-50 p-4">
        <p className="font-semibold text-blue-900">Go Pro</p>
        <p className="mt-1 text-sm text-blue-800">
          Unlock watchlist, alerts, saved searches, pop sorting, and the daily brief.
        </p>
        <Link
          href="/account"
          className="mt-3 inline-block rounded-full bg-blue-700 px-4 py-1.5 text-sm font-semibold text-white hover:bg-blue-800"
        >
          Upgrade
        </Link>
      </div>
    </main>
  );
}
