import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Charts — CardChart",
  description: "Open any card chart for sold comps, live listings, and an AI verdict.",
};

const PAGE = {
  bg: "#F7F6F2",
  text: "#17181C",
  text2: "#5B5F68",
  text3: "#84878F",
  accent: "#B6862E",
  accentInk: "#1A1408",
  accentSoft: "rgba(182,134,46,0.10)",
  surface: "#FFFFFF",
  border: "#E4E1D8",
  panel: "#1E2128",
  panelBorder: "#2A2E37",
  panelText: "#F6F7F9",
  panelText2: "#BAC0CB",
  panelGold: "#E0B94A",
} as const;

/** Featured demo slug used elsewhere on the home page — safe deep-link into /card/[slug]. */
const FEATURED_SLUG = "pokemon-base1-4-102";

export default function ChartsPage() {
  return (
    <main className="min-h-screen" style={{ background: PAGE.bg, color: PAGE.text }}>
      <div className="mx-auto max-w-[720px] px-4 py-12 sm:px-6">
        <p
          className="text-[11px] font-bold uppercase tracking-[0.14em]"
          style={{ color: PAGE.accent }}
        >
          Charts
        </p>
        <h1 className="mt-2 text-3xl font-extrabold tracking-[-0.02em]">
          Every card has a chart
        </h1>
        <p className="mt-3 max-w-xl text-[15px] leading-relaxed" style={{ color: PAGE.text2 }}>
          Search the catalogue or open a market mover to see sold history, active listings, and an
          AI buy / hold / sell read. Card detail lives at{" "}
          <code
            className="rounded px-1.5 py-0.5 text-[13px]"
            style={{ background: PAGE.accentSoft, color: PAGE.accent }}
          >
            /card/[slug]
          </code>
          .
        </p>

        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            href="/search"
            className="rounded-[11px] px-5 py-3 text-sm font-bold"
            style={{ background: PAGE.accent, color: PAGE.accentInk }}
          >
            Search cards
          </Link>
          <Link
            href="/ladder"
            className="rounded-[11px] border px-5 py-3 text-sm font-semibold"
            style={{ borderColor: PAGE.border, background: PAGE.surface, color: PAGE.text }}
          >
            Explore markets
          </Link>
        </div>

        <div
          className="mt-10 rounded-[18px] border p-5 shadow-[0_30px_70px_-24px_rgba(20,18,10,0.22)]"
          style={{
            background: PAGE.panel,
            borderColor: PAGE.panelBorder,
            color: PAGE.panelText,
          }}
        >
          <div
            className="text-[11px] font-bold uppercase tracking-[0.12em]"
            style={{ color: PAGE.panelGold }}
          >
            Featured chart
          </div>
          <h2 className="mt-2 text-xl font-bold">Charizard · Base Set</h2>
          <p className="mt-1 text-sm" style={{ color: PAGE.panelText2 }}>
            Open the sample card detail page with price history, comps, and listings.
          </p>
          <Link
            href={`/card/${FEATURED_SLUG}`}
            className="mt-4 inline-flex rounded-[10px] px-4 py-2.5 text-sm font-bold"
            style={{ background: PAGE.panelGold, color: PAGE.accentInk }}
          >
            View chart →
          </Link>
        </div>
      </div>
    </main>
  );
}
