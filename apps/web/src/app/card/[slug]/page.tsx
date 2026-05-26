import { CardActions } from "@/components/card-actions";
import { PriceChart } from "@/components/price-chart";
import { Card, CardContent, CardHeader, CardTitle } from "@tcgscan/ui";
import type { CardOut, CompOut, CompSummary, GradeVerdict, SourcePrices } from "@tcgscan/sdk-ts";
import {
  getCardBySlug,
  getChart,
  getCompSummary,
  getComps,
  getGradeRoi,
  getListings,
  getSourcePrices,
} from "@tcgscan/sdk-ts";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";

export const revalidate = 900;

type Props = { params: Promise<{ slug: string }> };

function cardImage(card: CardOut): string | null {
  const urls = card.image_urls;
  if (!urls) return null;
  const front = urls.front ?? urls.small ?? urls.hires;
  return typeof front === "string" ? front : null;
}

function PriceTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-3">
      <p className="text-xs uppercase tracking-wide text-zinc-500">{label}</p>
      <p className="mt-1 text-lg font-semibold">{value}</p>
    </div>
  );
}

function fmtUsd(n: number | null | undefined) {
  if (n == null) return "—";
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n);
}

function VerdictBadge({ verdict }: { verdict: GradeVerdict }) {
  const colors: Record<string, string> = {
    GRADE: "bg-green-100 text-green-800",
    SELL: "bg-red-100 text-red-800",
    HOLD: "bg-zinc-100 text-zinc-800",
    BUY: "bg-blue-100 text-blue-800",
  };
  return (
    <div className={`rounded-lg p-4 ${colors[verdict.action] ?? colors.HOLD}`}>
      <p className="font-semibold">{verdict.action}</p>
      <p className="mt-1 text-sm">{verdict.reason}</p>
    </div>
  );
}

export default async function CardDetailPage({ params }: Props) {
  const { slug } = await params;
  let card: CardOut;
  let comps: CompOut[];
  let summary: CompSummary;
  let chart: Awaited<ReturnType<typeof getChart>>;
  let sources: SourcePrices;
  let roi: GradeVerdict | null = null;
  let listings: Awaited<ReturnType<typeof getListings>> = [];

  try {
    card = await getCardBySlug(slug);
    [comps, summary, chart, sources, listings] = await Promise.all([
      getComps(card.id, 90),
      getCompSummary(card.id, 30),
      getChart(card.id, 90),
      getSourcePrices(card.id, 30),
      getListings(card.id, 10),
    ]);
    try {
      roi = await getGradeRoi(card.id, 9);
    } catch {
      roi = null;
    }
  } catch {
    notFound();
  }

  const img = cardImage(card);

  return (
    <main className="mx-auto max-w-4xl px-4 py-10">
      <Link href="/scan" className="text-sm text-zinc-500 hover:text-zinc-900">
        ← Scanner
      </Link>

      <div className="mt-6 grid gap-8 md:grid-cols-[240px_1fr]">
        <div className="relative aspect-[3/4] w-full max-w-[240px] overflow-hidden rounded-xl border bg-zinc-50">
          {img ? (
            <Image src={img} alt={card.name} fill className="object-contain p-2" sizes="240px" />
          ) : (
            <div className="flex h-full items-center justify-center text-sm text-zinc-400">No image</div>
          )}
        </div>

        <div>
          <p className="text-sm font-medium uppercase tracking-wide text-zinc-500">{card.game}</p>
          <h1 className="mt-1 text-3xl font-bold">{card.name}</h1>
          <p className="mt-2 text-zinc-600">
            {card.set_name ?? card.set_code} · {card.number} · {card.rarity}
          </p>

          <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <PriceTile label="30d median" value={fmtUsd(summary.median_usd)} />
            <PriceTile label="30d mean" value={fmtUsd(summary.mean_usd)} />
            <PriceTile label="30d low" value={fmtUsd(summary.min_usd)} />
            <PriceTile label="30d high" value={fmtUsd(summary.max_usd)} />
          </div>

          <div className="mt-4 grid grid-cols-3 gap-3">
            <PriceTile label="eBay" value={fmtUsd(sources.ebay_median_usd)} />
            <PriceTile label="TCGPlayer" value={fmtUsd(sources.tcgplayer_median_usd)} />
            <PriceTile label="Cardmarket" value={fmtUsd(sources.cardmarket_median_usd)} />
          </div>

          <p className="mt-4 text-sm text-zinc-500">{summary.count} sold comps in the last 30 days</p>

          <div className="mt-6">
            <CardActions cardId={card.id} cardName={card.name} />
          </div>
        </div>
      </div>

      <Card className="mt-10">
        <CardHeader>
          <CardTitle>90-day price chart</CardTitle>
        </CardHeader>
        <CardContent>
          <PriceChart data={chart} />
        </CardContent>
      </Card>

      {roi && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>Grade-ladder ROI</CardTitle>
          </CardHeader>
          <CardContent>
            <VerdictBadge verdict={roi} />
          </CardContent>
        </Card>
      )}

      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Active listings</CardTitle>
        </CardHeader>
        <CardContent>
          {listings.length === 0 ? (
            <p className="text-sm text-zinc-600">No active listings in the database yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b text-zinc-500">
                    <th className="py-2 pr-4">Price</th>
                    <th className="py-2 pr-4">Grade</th>
                    <th className="py-2">Source</th>
                  </tr>
                </thead>
                <tbody>
                  {listings.map((row, i) => (
                    <tr key={`${row.listed_at}-${i}`} className="border-b border-zinc-100">
                      <td className="py-2 pr-4 font-medium">
                        {row.listing_url ? (
                          <a
                            href={row.listing_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:underline"
                          >
                            {fmtUsd(row.price)}
                          </a>
                        ) : (
                          fmtUsd(row.price)
                        )}
                      </td>
                      <td className="py-2 pr-4">{row.grade ?? "raw"}</td>
                      <td className="py-2">{row.source}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Sold comps (90 days)</CardTitle>
        </CardHeader>
        <CardContent>
          {comps.length === 0 ? (
            <p className="text-sm text-zinc-600">
              No comps yet. Run <code className="rounded bg-zinc-100 px-1">pnpm db:seed</code>.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b text-zinc-500">
                    <th className="py-2 pr-4">Date</th>
                    <th className="py-2 pr-4">Price</th>
                    <th className="py-2 pr-4">Grade</th>
                    <th className="py-2">Source</th>
                  </tr>
                </thead>
                <tbody>
                  {comps.map((c, i) => (
                    <tr key={`${c.sold_at}-${i}`} className="border-b border-zinc-100">
                      <td className="py-2 pr-4">{new Date(c.sold_at).toLocaleDateString()}</td>
                      <td className="py-2 pr-4 font-medium">{fmtUsd(c.price)}</td>
                      <td className="py-2 pr-4">{c.grade ?? "raw"}</td>
                      <td className="py-2">{c.source}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </main>
  );
}
