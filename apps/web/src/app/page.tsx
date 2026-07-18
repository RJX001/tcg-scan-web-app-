export const dynamic = "force-dynamic";

import Link from "next/link";
import { Hanken_Grotesk, IBM_Plex_Mono, Spectral } from "next/font/google";
import type { CSSProperties, ReactNode } from "react";

const display = Spectral({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
  variable: "--font-display",
});
const body = Hanken_Grotesk({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
  variable: "--font-body",
});
const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-num",
});

/** Daylight light + dark contrast panel tokens (gold accent). */
const daylightStyle = {
  "--bg": "#F7F6F2",
  "--surface": "#FFFFFF",
  "--surface2": "#F1EFE9",
  "--border": "#E4E1D8",
  "--border-soft": "#ECE9E0",
  "--text": "#17181C",
  "--text2": "#5B5F68",
  "--text3": "#84878F",
  "--accent": "#B6862E",
  "--accent2": "#D4A53D",
  "--accent-ink": "#1A1408",
  "--accent-soft": "rgba(182,134,46,0.10)",
  "--up": "#1E9A6B",
  "--down": "#D6444B",
  "--hold": "#B6862E",
  "--up-bg": "rgba(30,154,107,0.13)",
  "--down-bg": "rgba(214,68,75,0.13)",
  "--hold-bg": "rgba(182,134,46,0.13)",
  "--eyebrow": "#B6862E",
  "--radius": "18px",
  "--radius-sm": "11px",
  "--shadow": "0 1px 2px rgba(23,24,28,0.05)",
  "--shadow-lg": "0 30px 70px -24px rgba(20,18,10,0.22)",
  "--panel": "#16181D",
  "--panel2": "#1E2128",
  "--panel-border": "#2A2E37",
  "--panel-text": "#F6F7F9",
  "--panel-text2": "#BAC0CB",
  "--panel-text3": "#8C93A1",
  "--panel-gold": "#E0B94A",
  "--panel-up": "#34D499",
  "--panel-down": "#FF6B70",
  background: "var(--bg)",
  color: "var(--text)",
  fontFamily: "var(--font-body), system-ui, sans-serif",
} as CSSProperties;

const FEATURES: { title: string; body: string; icon: ReactNode }[] = [
  {
    title: "Scan or search",
    body: "Point your camera or type a name. We identify the card, set and grade, then pull every recent sale.",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden>
        <rect x="3" y="5" width="18" height="14" rx="3" stroke="currentColor" strokeWidth="2" />
        <circle cx="12" cy="12" r="3.2" stroke="currentColor" strokeWidth="2" />
      </svg>
    ),
  },
  {
    title: "Real market data",
    body: "Sold prices and live listings from eBay, Cardmarket, TCGplayer and more — verified, with green checks.",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden>
        <path d="M4 19V5M4 19h16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        <path
          d="M8 15l3-3 3 2 4-6"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    ),
  },
  {
    title: "Portfolio & P&L",
    body: "Track raw, graded and sealed like a portfolio. See gains, losses and cost basis update daily.",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden>
        <rect x="3" y="6" width="18" height="13" rx="3" stroke="currentColor" strokeWidth="2" />
        <path d="M16 12h2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    title: "An AI verdict",
    body: "Buy, hold or sell — with confidence and the actual reasons. The thing no other tracker gives you.",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden>
        <path
          d="M12 3l2.2 5.6L20 12l-5.8 2.4L12 20l-2.2-5.6L4 12l5.8-2.4L12 3z"
          fill="currentColor"
        />
      </svg>
    ),
  },
];

type Verdict = "buy" | "hold" | "sell";

const SAMPLE_MOVERS: {
  rank: number;
  name: string;
  set: string;
  value: string;
  d24: string;
  d24Up: boolean;
  d7: string;
  d7Up: boolean;
  verdict: Verdict;
  href: string;
}[] = [
  {
    rank: 1,
    name: "Charizard",
    set: "Base Set · PSA 9",
    value: "£1,095",
    d24: "▲ 4.2%",
    d24Up: true,
    d7: "▲ 9.8%",
    d7Up: true,
    verdict: "buy",
    href: "/card/pokemon-base1-4-102",
  },
  {
    rank: 2,
    name: "Monkey D. Luffy",
    set: "OP-01 · Leader Parallel",
    value: "£185",
    d24: "▲ 12.4%",
    d24Up: true,
    d7: "▲ 22.0%",
    d7Up: true,
    verdict: "sell",
    href: "/market",
  },
  {
    rank: 3,
    name: "Blue-Eyes White Dragon",
    set: "LOB · 1st Ed · PSA 8",
    value: "£2,400",
    d24: "▲ 2.1%",
    d24Up: true,
    d7: "▼ 1.4%",
    d7Up: false,
    verdict: "hold",
    href: "/market",
  },
  {
    rank: 4,
    name: "Pikachu Illustrator",
    set: "Promo · CGC 7",
    value: "£312,000",
    d24: "▲ 1.8%",
    d24Up: true,
    d7: "▲ 4.0%",
    d7Up: true,
    verdict: "hold",
    href: "/card/pokemon-base1-58-102",
  },
  {
    rank: 5,
    name: "Mox Sapphire",
    set: "Beta · BGS 8.5",
    value: "£9,750",
    d24: "▼ 3.1%",
    d24Up: false,
    d7: "▼ 5.2%",
    d7Up: false,
    verdict: "sell",
    href: "/market",
  },
  {
    rank: 6,
    name: "Umbreon VMAX",
    set: "Evolving Skies · Alt Art",
    value: "£540",
    d24: "▲ 6.7%",
    d24Up: true,
    d7: "▲ 14.3%",
    d7Up: true,
    verdict: "buy",
    href: "/market",
  },
];

const FREE_PERKS = [
  "Browse 1M+ cards",
  "Daily market indices",
  "Latest 5 sold prices",
  "One portfolio",
];
const PRO_PERKS = [
  "Full sales history",
  "AI Buy/Hold/Sell verdicts",
  "Price & verdict alerts",
  "Unlimited portfolios",
  "Population & ROI tools",
];

function verdictStyle(v: Verdict) {
  if (v === "buy") return { label: "▲ Buy", color: "var(--up)", bg: "var(--up-bg)" };
  if (v === "sell") return { label: "▼ Sell", color: "var(--down)", bg: "var(--down-bg)" };
  return { label: "● Hold", color: "var(--hold)", bg: "var(--hold-bg)" };
}

export default function LandingPage() {
  return (
    <main
      className={`${display.variable} ${body.variable} ${mono.variable} min-h-[calc(100vh-57px)]`}
      style={daylightStyle}
    >
      <div className="mx-auto max-w-[1200px] px-6">
        {/* Hero */}
        <section className="grid grid-cols-1 items-center gap-11 py-10 lg:grid-cols-[1.05fr_.95fr] lg:py-14">
          <div>
            <div className="inline-flex items-center gap-2 whitespace-nowrap rounded-full bg-[var(--accent-soft)] px-3 py-1.5 text-[11px] font-bold uppercase tracking-[0.12em] text-[var(--eyebrow)]">
              Pokémon · MTG · Yu-Gi-Oh! · One Piece · Lorcana · Riftbound · and many more
            </div>
            <h1
              className="mt-[18px] text-[clamp(36px,5vw,56px)] font-extrabold leading-[1.03] tracking-[-0.035em]"
              style={{ fontFamily: "var(--font-display), serif" }}
            >
              The whole card market —
              <br />
              and what to <span className="text-[var(--accent)]">do</span> about it.
            </h1>
            <p className="mt-[18px] max-w-[500px] text-[16.5px] leading-relaxed text-[var(--text2)]">
              Scan or search any card. See real sold prices and live listings from every marketplace,
              track your collection like a portfolio, and get an AI read on whether to{" "}
              <b className="text-[var(--text)]">buy, hold or sell</b> — explained, not guessed.
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <Link
                href="/scan"
                className="rounded-xl bg-[var(--accent)] px-6 py-3.5 text-[14.5px] font-bold text-[var(--accent-ink)] transition hover:opacity-90"
              >
                Scan a card
              </Link>
              <Link
                href="/market"
                className="rounded-xl border border-[var(--border)] bg-transparent px-[22px] py-3.5 text-[14.5px] font-semibold text-[var(--text)] transition hover:bg-[var(--surface2)]"
              >
                Explore markets
              </Link>
            </div>
            <div className="mt-9 flex flex-wrap gap-8">
              {[
                ["25+", "TCGs tracked"],
                ["100M+", "Verified sales"],
                ["£8", "Pro / month"],
              ].map(([n, label]) => (
                <div key={label}>
                  <div
                    className="text-[23px] font-extrabold tabular-nums"
                    style={{ fontFamily: "var(--font-num), monospace" }}
                  >
                    {n}
                  </div>
                  <div className="mt-0.5 text-[12.5px] text-[var(--text3)]">{label}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Dark panel preview card */}
          <div
            className="cc-panel rounded-[var(--radius)] border border-[var(--panel-border)] bg-[var(--panel)] p-5 text-[var(--panel-text)] shadow-[var(--shadow-lg)]"
          >
            <div className="flex gap-4">
              <div
                className="relative flex aspect-[5/7] w-[104px] shrink-0 items-end justify-center overflow-hidden rounded-xl border border-[var(--panel-border)] pb-2"
                style={{
                  background:
                    "repeating-linear-gradient(135deg,var(--panel2),var(--panel2) 7px,var(--panel) 7px,var(--panel) 14px)",
                }}
              >
                <span
                  className="text-[8.5px] tracking-[0.1em] text-[var(--panel-text3)]"
                  style={{ fontFamily: "var(--font-num), monospace" }}
                >
                  CARD ART
                </span>
                <span
                  className="pointer-events-none absolute inset-0 opacity-[0.16]"
                  style={{
                    background:
                      "linear-gradient(115deg,transparent 30%,var(--panel-gold) 48%,transparent 66%)",
                  }}
                />
              </div>
              <div className="flex-1">
                <div
                  className="text-[19px] font-bold"
                  style={{ fontFamily: "var(--font-display), serif" }}
                >
                  Charizard
                </div>
                <div className="mt-0.5 text-[12.5px] text-[var(--panel-text2)]">
                  Base Set · 1999 · PSA 9
                </div>
                <div
                  className="mt-3 text-[28px] font-extrabold tabular-nums"
                  style={{ fontFamily: "var(--font-num), monospace" }}
                >
                  £1,095
                </div>
                <div className="mt-0.5 text-[13px] font-bold text-[var(--panel-up)]">
                  ▲ 4.2% today · ▲ 9.8% 7d
                </div>
              </div>
            </div>
            <div className="mt-[18px] flex items-center gap-2.5 border-t border-[var(--panel-border)] pt-4">
              <span className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border border-[var(--panel-border)] bg-white/[0.06] px-3.5 py-2 text-[13.5px] font-bold text-[var(--panel-up)]">
                ▲ BUY
              </span>
              <span className="text-[13px] text-[var(--panel-text2)]">78% confidence</span>
              <span className="ml-auto text-[10.5px] font-bold uppercase tracking-[0.12em] text-[var(--panel-gold)]">
                ★ AI Verdict
              </span>
            </div>
          </div>
        </section>

        {/* Sources strip */}
        <div className="flex flex-wrap items-center gap-6 border-y border-[var(--border-soft)] py-[18px]">
          <span className="text-[11px] font-bold uppercase tracking-[0.1em] text-[var(--text3)]">
            Sold data from
          </span>
          {["eBay", "Cardmarket", "TCGplayer", "Goldin"].map((s) => (
            <span key={s} className="text-sm font-bold text-[var(--text2)]">
              {s}
            </span>
          ))}
          <span className="ml-auto text-[11px] font-bold uppercase tracking-[0.1em] text-[var(--text3)]">
            Pop reports
          </span>
          <span className="text-sm font-bold text-[var(--text2)]">PSA · BGS · CGC · SGC</span>
        </div>

        {/* Features */}
        <section className="pb-2 pt-12">
          <div className="text-[11px] font-bold uppercase tracking-[0.14em] text-[var(--eyebrow)]">
            Why CardChart
          </div>
          <h2
            className="mt-2.5 max-w-[620px] text-[30px] font-extrabold tracking-[-0.02em]"
            style={{ fontFamily: "var(--font-display), serif" }}
          >
            Everyone shows prices. We tell you what they mean.
          </h2>
          <div className="mt-7 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {FEATURES.map((f) => (
              <div
                key={f.title}
                className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-[22px] shadow-[var(--shadow)]"
              >
                <div className="mb-3.5 flex h-[42px] w-[42px] items-center justify-center rounded-xl bg-[var(--accent-soft)] text-[var(--accent)]">
                  {f.icon}
                </div>
                <h3
                  className="text-base font-bold"
                  style={{ fontFamily: "var(--font-display), serif" }}
                >
                  {f.title}
                </h3>
                <p className="mt-1.5 text-[13.5px] leading-[1.55] text-[var(--text2)]">{f.body}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Movers */}
        <section className="pb-2 pt-11">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <div className="text-[11px] font-bold uppercase tracking-[0.14em] text-[var(--eyebrow)]">
                Movers today
              </div>
              <h2
                className="mt-2 text-2xl font-extrabold tracking-[-0.02em]"
                style={{ fontFamily: "var(--font-display), serif" }}
              >
                What&apos;s moving right now
              </h2>
            </div>
            <Link
              href="/market"
              className="rounded-[10px] border border-[var(--border)] px-3.5 py-2 text-[13px] font-semibold text-[var(--text)] transition hover:bg-[var(--surface2)]"
            >
              View all markets
            </Link>
          </div>
          <div className="cc-panel mt-[18px] overflow-x-auto rounded-[var(--radius)] border border-[var(--panel-border)] bg-[var(--panel)] text-[var(--panel-text)] shadow-[var(--shadow)]">
            <div className="min-w-[640px]">
              <div className="grid grid-cols-[34px_2.4fr_1fr_1fr_1fr_1.1fr] gap-3 border-b border-[var(--panel-border)] px-[18px] py-3 text-[10.5px] font-bold uppercase tracking-[0.06em] text-[var(--panel-text3)]">
                <div>#</div>
                <div>Card</div>
                <div>Value</div>
                <div>24h</div>
                <div>7d</div>
                <div>Verdict</div>
              </div>
              {SAMPLE_MOVERS.map((row) => {
                const v = verdictStyle(row.verdict);
                return (
                  <Link
                    key={row.rank}
                    href={row.href}
                    className="grid grid-cols-[34px_2.4fr_1fr_1fr_1fr_1.1fr] items-center gap-3 border-b border-[var(--panel-border)] px-[18px] py-3.5 transition last:border-b-0 hover:bg-white/[0.03]"
                  >
                    <div
                      className="text-[13px] font-bold text-[var(--panel-text3)]"
                      style={{ fontFamily: "var(--font-num), monospace" }}
                    >
                      {row.rank}
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="h-11 w-8 shrink-0 rounded-md border border-[var(--panel-border)] bg-[var(--panel2)]" />
                      <div>
                        <div className="text-sm font-semibold">{row.name}</div>
                        <div className="mt-px text-xs text-[var(--panel-text3)]">{row.set}</div>
                      </div>
                    </div>
                    <div
                      className="text-sm font-bold tabular-nums"
                      style={{ fontFamily: "var(--font-num), monospace" }}
                    >
                      {row.value}
                    </div>
                    <div
                      className="text-[13px] font-semibold tabular-nums"
                      style={{
                        fontFamily: "var(--font-num), monospace",
                        color: row.d24Up ? "var(--panel-up)" : "var(--panel-down)",
                      }}
                    >
                      {row.d24}
                    </div>
                    <div
                      className="text-[13px] font-semibold tabular-nums"
                      style={{
                        fontFamily: "var(--font-num), monospace",
                        color: row.d7Up ? "var(--panel-up)" : "var(--panel-down)",
                      }}
                    >
                      {row.d7}
                    </div>
                    <div>
                      <span
                        className="whitespace-nowrap rounded-[7px] px-2.5 py-1 text-[11.5px] font-bold"
                        style={{ background: v.bg, color: v.color }}
                      >
                        {v.label}
                      </span>
                    </div>
                  </Link>
                );
              })}
            </div>
          </div>
        </section>

        {/* Pricing */}
        <section className="pb-16 pt-12">
          <div className="text-center">
            <div className="text-[11px] font-bold uppercase tracking-[0.14em] text-[var(--eyebrow)]">
              Pricing
            </div>
            <h2
              className="mt-2 text-[28px] font-extrabold tracking-[-0.02em]"
              style={{ fontFamily: "var(--font-display), serif" }}
            >
              Start free. Go Pro when you&apos;re serious.
            </h2>
          </div>
          <div className="mx-auto mt-7 grid max-w-[760px] grid-cols-1 gap-[18px] sm:grid-cols-2">
            <div className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-[26px] shadow-[var(--shadow)]">
              <div
                className="text-[17px] font-bold"
                style={{ fontFamily: "var(--font-display), serif" }}
              >
                Free
              </div>
              <div
                className="mt-2 text-[34px] font-extrabold"
                style={{ fontFamily: "var(--font-num), monospace" }}
              >
                £0
              </div>
              <div className="text-[13px] text-[var(--text3)]">Browse, search, daily indices</div>
              <div className="mt-[18px] flex flex-col gap-2.5">
                {FREE_PERKS.map((p) => (
                  <div key={p} className="flex gap-2 text-[13.5px] text-[var(--text2)]">
                    <span className="text-[var(--up)]">✓</span>
                    {p}
                  </div>
                ))}
              </div>
            </div>
            <div className="relative rounded-[var(--radius)] border-[1.5px] border-[var(--accent)] bg-[var(--surface)] p-[26px] shadow-[var(--shadow-lg)]">
              <div className="absolute -top-[11px] right-[18px] whitespace-nowrap rounded-full bg-[var(--accent)] px-2.5 py-1 text-[10.5px] font-bold uppercase tracking-[0.1em] text-[var(--accent-ink)]">
                Popular
              </div>
              <div
                className="text-[17px] font-bold text-[var(--accent)]"
                style={{ fontFamily: "var(--font-display), serif" }}
              >
                Pro
              </div>
              <div
                className="mt-2 text-[34px] font-extrabold"
                style={{ fontFamily: "var(--font-num), monospace" }}
              >
                £8
              </div>
              <div className="text-[13px] text-[var(--text3)]">
                Full history, verdicts, alerts, portfolio
              </div>
              <div className="mt-[18px] flex flex-col gap-2.5">
                {PRO_PERKS.map((p) => (
                  <div key={p} className="flex gap-2 text-[13.5px] text-[var(--text)]">
                    <span className="text-[var(--accent)]">✓</span>
                    {p}
                  </div>
                ))}
              </div>
              <Link
                href="/scan"
                className="mt-[22px] block w-full rounded-[11px] bg-[var(--accent)] py-3.5 text-center text-sm font-bold text-[var(--accent-ink)] transition hover:opacity-90"
              >
                Start 7-day free trial
              </Link>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
