import { Button, Card, CardContent, CardHeader, CardTitle } from "@tcgscan/ui";
import Link from "next/link";

const FEATURES = [
  {
    title: "Scan any card",
    desc: "Upload or use your camera. Get top matches, condition estimate, and grading ROI.",
    href: "/scan",
    cta: "Open scanner",
  },
  {
    title: "Cross-marketplace comps",
    desc: "eBay sold, TCGPlayer, Cardmarket — 30-day median, chart, and active listings.",
    href: "/card/pokemon-base1-4-102",
    cta: "View Charizard demo",
  },
  {
    title: "Portfolio & alerts",
    desc: "Track collection value and set price alerts when cards move.",
    href: "/portfolio",
    cta: "View portfolio",
  },
  {
    title: "Daily brief",
    desc: "Pro subscribers get a morning digest of portfolio movers and market trends.",
    href: "/digest",
    cta: "Preview digest",
  },
];

export default function LandingPage() {
  return (
    <main className="mx-auto flex min-h-[calc(100vh-57px)] max-w-4xl flex-col gap-10 px-4 py-16">
      <div className="text-center">
        <p className="text-sm font-medium uppercase tracking-wider text-zinc-500">TCG Scan</p>
        <h1 className="mt-2 text-4xl font-bold tracking-tight sm:text-5xl">
          Scan once. Know the market.
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-lg text-zinc-600">
          Price guide for every modern TCG and sports card — sold comps, active listings, condition
          estimates, and grading ROI verdicts across eBay, TCGPlayer, and Cardmarket.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <Button asChild>
            <Link href="/scan">Try the scanner</Link>
          </Button>
          <Button asChild variant="outline">
            <Link href="/search">Search catalog</Link>
          </Button>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {FEATURES.map((f) => (
          <Card key={f.href}>
            <CardHeader>
              <CardTitle className="text-lg">{f.title}</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              <p className="text-sm text-zinc-600">{f.desc}</p>
              <Button asChild variant="outline" size="sm" className="w-fit">
                <Link href={f.href}>{f.cta}</Link>
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="border-blue-100 bg-blue-50/50">
        <CardContent className="pt-6 text-center text-sm text-zinc-700">
          <strong>Local demo:</strong> API at{" "}
          <a href="http://localhost:8000/v1/health" className="text-blue-600 underline">
            localhost:8000
          </a>{" "}
          · Base Set seed cards with 30-day comps across eBay, TCGPlayer, and Cardmarket.
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Demo cards</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap justify-center gap-2">
          {[
            ["pokemon-base1-4-102", "Charizard"],
            ["pokemon-base1-2-102", "Blastoise"],
            ["pokemon-base1-15-102", "Venusaur"],
            ["pokemon-base1-58-102", "Pikachu"],
            ["pokemon-base1-10-102", "Mewtwo"],
            ["pokemon-base1-1-102", "Alakazam"],
            ["pokemon-base1-6-102", "Gyarados"],
          ].map(([slug, name]) => (
            <Button key={slug} asChild variant="outline" size="sm">
              <Link href={`/card/${slug}`}>{name}</Link>
            </Button>
          ))}
        </CardContent>
      </Card>
    </main>
  );
}
