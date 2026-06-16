import { CardActions } from "@/components/card-actions";
import { CompsTable } from "@/components/comps-table";
import { ListingsTable } from "@/components/listings-table";
import { MarketplacePrices } from "@/components/marketplace-prices";
import { PriceChart } from "@/components/price-chart";
import { Card, CardContent, CardHeader, CardTitle } from "@tcgscan/ui";
import type {
  CardOut,
  CompOut,
  CompSummary,
  GradeVerdict,
  PopulationOut,
  SourcePrices,
} from "@tcgscan/sdk-ts";
import {
  getCardBySlug,
  getChart,
  getCompSummary,
  getComps,
  getGradeRoi,
  getListings,
  getPopulation,
  getSourcePrices,
} from "@tcgscan/sdk-ts";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Money, Num } from "@/lib/currency";

export const revalidate = 900;

type Props = { params: Promise<{ slug: string }> };

function cardImage(card: CardOut): string | null {
  const urls = card.image_urls;
  if (!urls) return null;
  const front = urls.front ?? urls.small ?? urls.hires;
  return typeof front === "string" ? front : null;
}

function PriceTile({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-3">
      <p className="text-xs uppercase tracking-wide text-zinc-500">{label}</p>
      <p className="mt-1 text-lg font-semibold">{value}</p>
    </div>
  );
}

function popReportUrl(card: CardOut): string {
  const q = encodeURIComponent(`${card.name} ${card.set_name ?? card.set_code ?? ""}`.trim());
  return `https://www.psacard.com/pop/search?q=${q}`;
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
  let population: PopulationOut | null = null;

  try {
    card = await getCardBySlug(slug);
    [comps, summary, chart, sources, listings] = await Promise.all([
      getComps(card.id, 90),
      getCompSummary(card.id, 30),
      getChart(card.id, 90),
      getSourcePrices(card.id, 30),
      getListings(card.id, 50),
    ]);
    try {
      roi = await getGradeRoi(card.id, 9);
    } catch {
      roi = null;
    }
    try {
      population = await getPopulation(card.id);
    } catch {
      population = null;
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
            {card.price_status === "available" && summary.count >= 5 ? (
              <>
                <PriceTile label="30d median" value={<Money usd={summary.median_usd} />} />
                <PriceTile label="30d mean" value={<Money usd={summary.mean_usd} />} />
                <PriceTile label="30d low" value={<Money usd={summary.min_usd} />} />
                <PriceTile label="30d high" value={<Money usd={summary.max_usd} />} />
              </>
            ) : (
              <div className="col-span-2 rounded-lg border border-amber-200 bg-amber-50 p-4 sm:col-span-4">
                <p className="text-sm font-medium text-amber-900">Live pricing unavailable</p>
                <p className="mt-1 text-sm text-amber-800">
                  Live pricing unavailable until marketplace/sold comp sources are connected.
                  Catalogue metadata is shown below.
                </p>
              </div>
            )}
          </div>

          <div className="mt-4">
            <MarketplacePrices cardId={card.id} initial={sources} />
          </div>

          <p className="mt-4 text-sm text-zinc-500">{summary.count} sold comps in the last 30 days</p>

          {population && population.total > 0 ? (
            <div className="mt-4">
              <p className="text-xs uppercase tracking-wide text-zinc-500">
                Graded population · <Num n={population.total} /> total
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                {population.entries.map((e) => (
                  <span
                    key={`${e.grade_company}-${e.grade}`}
                    className="rounded border border-zinc-200 bg-zinc-50 px-2 py-1 text-xs text-zinc-700"
                  >
                    {e.grade_company} {e.grade}:{" "}
                    <span className="font-semibold">
                      <Num n={e.pop_count} />
                    </span>
                  </span>
                ))}
              </div>
            </div>
          ) : null}

          <p className="mt-2 text-sm">
            <a
              href={popReportUrl(card)}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:underline"
            >
              PSA pop report →
            </a>
          </p>

          <div className="mt-6">
            <CardActions cardId={card.id} cardName={card.name} medianUsd={summary.median_usd} />
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
            <p className="text-sm text-zinc-600">
              Live listings pending marketplace source approval.
            </p>
          ) : (
            <ListingsTable listings={listings} />
          )}
        </CardContent>
      </Card>

      {card.metadata && Object.keys(card.metadata).length > 0 ? (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>Catalogue metadata</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid gap-2 text-sm sm:grid-cols-2">
              {Object.entries(card.metadata).map(([key, value]) => (
                <div key={key}>
                  <dt className="text-xs uppercase tracking-wide text-zinc-500">{key.replaceAll("_", " ")}</dt>
                  <dd className="mt-0.5 break-words text-zinc-800">
                    {typeof value === "object" ? JSON.stringify(value) : String(value)}
                  </dd>
                </div>
              ))}
            </dl>
          </CardContent>
        </Card>
      ) : null}

      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Sold comps (90 days)</CardTitle>
        </CardHeader>
        <CardContent>
          <CompsTable comps={comps} />
        </CardContent>
      </Card>
    </main>
  );
}
