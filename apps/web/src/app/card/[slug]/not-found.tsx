import Link from "next/link";

const PAGE = {
  bg: "#F7F6F2",
  text: "#17181C",
  text2: "#5B5F68",
  text3: "#84878F",
  accent: "#B6862E",
  accentInk: "#1A1408",
  surface: "#FFFFFF",
  border: "#E4E1D8",
} as const;

export default function CardNotFound() {
  return (
    <main className="min-h-[60vh]" style={{ background: PAGE.bg, color: PAGE.text }}>
      <div className="mx-auto max-w-lg px-4 py-16 text-center">
        <p
          className="text-sm font-bold uppercase tracking-[0.14em]"
          style={{ color: PAGE.accent }}
        >
          Card not found
        </p>
        <h1 className="mt-2 text-2xl font-extrabold tracking-tight">
          We could not find that card
        </h1>
        <p className="mt-3 text-sm" style={{ color: PAGE.text2 }}>
          The catalogue link may be outdated, or the card has not been imported yet.
        </p>
        <div className="mt-8 flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
          <Link
            href="/search"
            className="rounded-[11px] px-4 py-2.5 text-sm font-bold"
            style={{ background: PAGE.accent, color: PAGE.accentInk }}
          >
            Search cards
          </Link>
          <Link
            href="/ladder"
            className="rounded-[11px] border px-4 py-2.5 text-sm font-semibold"
            style={{ borderColor: PAGE.border, background: PAGE.surface, color: PAGE.text }}
          >
            Browse markets
          </Link>
          <Link
            href="/scan"
            className="text-sm font-semibold hover:underline"
            style={{ color: PAGE.accent }}
          >
            Open scanner
          </Link>
        </div>
      </div>
    </main>
  );
}
