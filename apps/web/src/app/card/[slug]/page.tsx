import { Card, CardContent, CardHeader, CardTitle } from "@tcgscan/ui";
import type { CardOut, CompOut, CompSummary } from "@tcgscan/sdk-ts";
import { getCardBySlug, getCompSummary, getComps } from "@tcgscan/sdk-ts";
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

export default async function CardDetailPage({ params }: Props) {
  const { slug } = await params;
  let card: CardOut;
  let comps: CompOut[];
  let summary: CompSummary;

  try {
    card = await getCardBySlug(slug);
    [comps, summary] = await Promise.all([
      getComps(card.id, 30),
      getCompSummary(card.id, 30),
    ]);
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

          <p className="mt-4 text-sm text-zinc-500">
            {summary.count} eBay sold comps in the last 30 days
          </p>
        </div>
      </div>

      <Card className="mt-10">
        <CardHeader>
          <CardTitle>Recent sold comps</CardTitle>
        </CardHeader>
        <CardContent>
          {comps.length === 0 ? (
            <p className="text-sm text-zinc-600">
              No comps yet. Run{" "}
              <code className="rounded bg-zinc-100 px-1">pnpm db:seed</code> or{" "}
              <code className="rounded bg-zinc-100 px-1">ingest:pricing</code> with eBay credentials.
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
                      <td className="py-2 pr-4 font-medium">
                        {fmtUsd(c.price)}
                        {c.currency !== "USD" && (
                          <span className="ml-1 text-xs text-zinc-400">{c.currency}</span>
                        )}
                      </td>
                      <td className="py-2 pr-4">{c.grade ?? "raw"}</td>
                      <td className="py-2">
                        {c.listing_url ? (
                          <a
                            href={c.listing_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:underline"
                          >
                            {c.source}
                          </a>
                        ) : (
                          c.source
                        )}
                      </td>
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
