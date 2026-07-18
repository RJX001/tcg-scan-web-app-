import { CardActions } from "@/components/card-actions";
import { CompsTable } from "@/components/comps-table";
import { ListingsTable } from "@/components/listings-table";
import { MarketplacePrices } from "@/components/marketplace-prices";
import { PriceChart } from "@/components/price-chart";
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

/** Daylight tokens — scoped to this page only (no globals.css edits). */
const PAGE = {
  bg: "#F7F6F2",
  text: "#17181C",
  text2: "#5B5F68",
  text3: "#84878F",
  accent: "#B6862E",
  accentSoft: "rgba(182,134,46,0.10)",
  surface: "#FFFFFF",
  border: "#E4E1D8",
  up: "#1E9A6B",
  down: "#D6444B",
  panel: "#1E2128",
  panel2: "#252932",
  panelBorder: "#2A2E37",
  panelText: "#F6F7F9",
  panelText2: "#BAC0CB",
  panelText3: "#8C93A1",
  panelGold: "#E0B94A",
  panelUp: "#34D499",
} as const;

function cardImage(card: CardOut): string | null {
  if (typeof card.image_url === "string" && card.image_url) return card.image_url;
  const urls = card.image_urls;
  if (!urls) return null;
  const front = urls.front ?? urls.small ?? urls.hires ?? urls.large;
  return typeof front === "string" ? front : null;
}

function metaValue(
  meta: Record<string, unknown> | null | undefined,
  ...keys: string[]
): string | null {
  if (!meta) return null;
  for (const key of keys) {
    const v = meta[key];
    if (v == null || v === "") continue;
    if (typeof v === "string" && v.trim()) return v.trim();
    if (typeof v === "number" || typeof v === "boolean") return String(v);
    if (Array.isArray(v) && v.length > 0) {
      return v
        .map((item) => (typeof item === "string" || typeof item === "number" ? String(item) : null))
        .filter(Boolean)
        .join(", ");
    }
  }
  return null;
}

/** Pull curated catalogue fields — never dump the raw metadata object. */
function catalogueFields(card: CardOut) {
  const meta = card.metadata ?? undefined;
  return {
    type: metaValue(meta, "type_line", "card_type", "supertype", "types", "type"),
    colour: metaValue(meta, "colour", "color", "colors", "color_identity"),
    cost: metaValue(meta, "mana_cost", "cost", "cmc"),
    power: metaValue(meta, "power", "hp", "atk"),
    effect: metaValue(meta, "oracle_text", "effect", "description", "card_text", "desc"),
  };
}

function popReportUrl(card: CardOut): string {
  const q = encodeURIComponent(`${card.name} ${card.set_name ?? card.set_code ?? ""}`.trim());
  return `https://www.psacard.com/pop/search?q=${q}`;
}

function formatSoldAgo(iso: string | undefined): string {
  if (!iso) return "—";
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return "—";
  const days = Math.floor((Date.now() - t) / 86_400_000);
  if (days <= 0) return "Today";
  if (days === 1) return "1 day ago";
  if (days < 30) return `${days} days ago`;
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function AiVerdict({ verdict }: { verdict: GradeVerdict }) {
  const tone =
    verdict.action === "BUY" || verdict.action === "GRADE"
      ? { color: PAGE.panelUp, arrow: "▲" }
      : verdict.action === "SELL"
        ? { color: "#FF6B70", arrow: "▼" }
        : { color: PAGE.panelGold, arrow: "●" };

  const bullets = [
    verdict.reason,
    verdict.raw_median_usd != null ? (
      <>
        Raw median ≈ <Money usd={verdict.raw_median_usd} />
      </>
    ) : null,
    verdict.graded_estimate_usd != null ? (
      <>
        Graded estimate ≈ <Money usd={verdict.graded_estimate_usd} />
      </>
    ) : null,
    verdict.expected_profit_usd != null ? (
      <>
        Expected profit ≈ <Money usd={verdict.expected_profit_usd} />
      </>
    ) : null,
  ].filter(Boolean);

  return (
    <div
      className="rounded-[18px] p-[1.5px]"
      style={{
        background: `linear-gradient(135deg, ${PAGE.panelUp}, ${PAGE.panelGold})`,
      }}
    >
      <div
        className="rounded-[16.5px] p-6"
        style={{ background: PAGE.panel, color: PAGE.panelText }}
      >
        <div
          className="text-[11px] font-bold uppercase tracking-[0.14em]"
          style={{ color: PAGE.panelGold }}
        >
          ★ AI Verdict
        </div>
        <div className="mt-3.5 flex flex-wrap items-center gap-4">
          <span
            className="inline-flex items-center gap-2 rounded-[14px] border px-5 py-2.5 text-[22px] font-extrabold"
            style={{
              borderColor: PAGE.panelBorder,
              background: "rgba(255,255,255,0.06)",
              color: tone.color,
            }}
          >
            {tone.arrow} {verdict.action}
          </span>
        </div>
        {bullets.length > 0 ? (
          <div className="mt-5 grid gap-3 sm:grid-cols-2">
            {bullets.map((b, i) => (
              <div
                key={i}
                className="flex gap-2.5 rounded-xl border px-3.5 py-3 text-[13.5px] leading-snug"
                style={{
                  background: PAGE.panel2,
                  borderColor: PAGE.panelBorder,
                  color: PAGE.panelText,
                }}
              >
                <span aria-hidden>▸</span>
                <span>{b}</span>
              </div>
            ))}
          </div>
        ) : null}
        <div
          className="mt-5 flex flex-wrap items-end justify-between gap-4 border-t pt-4"
          style={{ borderColor: PAGE.panelBorder }}
        >
          <div className="flex gap-6">
            {verdict.graded_estimate_usd != null ? (
              <div>
                <div
                  className="text-[11px] font-bold uppercase tracking-[0.08em]"
                  style={{ color: PAGE.panelText3 }}
                >
                  Graded target
                </div>
                <div className="mt-0.5 text-lg font-extrabold tabular-nums">
                  <Money usd={verdict.graded_estimate_usd} />
                </div>
              </div>
            ) : null}
            {verdict.grading_cost_usd != null ? (
              <div>
                <div
                  className="text-[11px] font-bold uppercase tracking-[0.08em]"
                  style={{ color: PAGE.panelText3 }}
                >
                  Grading cost
                </div>
                <div className="mt-0.5 text-lg font-extrabold tabular-nums">
                  <Money usd={verdict.grading_cost_usd} />
                </div>
              </div>
            ) : null}
          </div>
          <p className="max-w-[300px] text-[11px]" style={{ color: PAGE.panelText3 }}>
            CardChart&apos;s verdict is informational only and not financial advice.
          </p>
        </div>
      </div>
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
  const fields = catalogueFields(card);
  const number = card.number ?? card.card_number;
  const setLabel = card.set_name ?? card.set_code ?? null;
  const hasPricing = card.price_status === "available" && summary.count >= 5;
  const displayPrice = hasPricing
    ? summary.median_usd
    : (card.current_value ?? summary.median_usd ?? null);
  const lastSold = comps[0]?.sold_at;
  const chipBits = [card.rarity, number ? `#${number}` : null].filter(Boolean);

  return (
    <main className="min-h-screen" style={{ background: PAGE.bg, color: PAGE.text }}>
      <div className="mx-auto max-w-[1200px] px-4 py-8 sm:px-6 sm:py-10">
        <Link
          href="/search"
          className="text-sm font-medium hover:underline"
          style={{ color: PAGE.text3 }}
        >
          ← Search cards
        </Link>

        <div className="mt-6 grid items-start gap-7 lg:grid-cols-[300px_1fr]">
          {/* Sticky left dark panel */}
          <aside
            className="rounded-[18px] border p-[18px] shadow-[0_30px_70px_-24px_rgba(20,18,10,0.22)] lg:sticky lg:top-24"
            style={{
              background: PAGE.panel,
              borderColor: PAGE.panelBorder,
              color: PAGE.panelText,
            }}
          >
            <div
              className="relative aspect-[5/7] overflow-hidden rounded-xl border"
              style={{
                borderColor: PAGE.panelBorder,
                background: `repeating-linear-gradient(135deg, ${PAGE.panel2}, ${PAGE.panel2} 9px, ${PAGE.panel} 9px, ${PAGE.panel} 18px)`,
              }}
            >
              {img ? (
                <Image
                  src={img}
                  alt={card.name}
                  fill
                  className="object-contain p-2"
                  sizes="300px"
                  priority
                />
              ) : (
                <div
                  className="flex h-full items-center justify-center text-xs font-bold tracking-[0.2em]"
                  style={{ color: PAGE.panelText3 }}
                >
                  CARD ART
                </div>
              )}
            </div>

            <div className="mt-3.5 flex flex-wrap items-center justify-between gap-2">
              <span className="text-[12.5px]" style={{ color: PAGE.panelText3 }}>
                {chipBits.length > 0 ? (
                  <>
                    {chipBits.join(" · ")}
                    {card.rarity?.toLowerCase().includes("secret") ||
                    card.rarity?.toLowerCase().includes("illustration") ? (
                      <span className="ml-1 font-bold" style={{ color: PAGE.panelGold }}>
                        ★ Grail
                      </span>
                    ) : null}
                  </>
                ) : (
                  "Catalogue"
                )}
              </span>
              <span className="text-base font-extrabold tabular-nums">
                {displayPrice != null ? <Money usd={displayPrice} /> : "—"}
              </span>
            </div>

            <div
              className="mt-3.5 grid grid-cols-2 gap-px overflow-hidden rounded-[10px] border"
              style={{ background: PAGE.panelBorder, borderColor: PAGE.panelBorder }}
            >
              {(
                [
                  ["Game", card.game],
                  ["Set", setLabel ?? "—"],
                  ["Number", number ?? "—"],
                  ["Rarity", card.rarity ?? "—"],
                  [
                    "30d sales",
                    hasPricing ? <Num n={summary.count} /> : "Pending",
                  ],
                  [
                    "Listings",
                    listings.length > 0 ? <Num n={listings.length} /> : "—",
                  ],
                ] as const
              ).map(([k, v]) => (
                <div key={k} className="px-3 py-2.5" style={{ background: PAGE.panel }}>
                  <div
                    className="text-[10px] font-bold uppercase tracking-[0.06em]"
                    style={{ color: PAGE.panelText3 }}
                  >
                    {k}
                  </div>
                  <div className="mt-0.5 truncate text-sm font-bold" title={typeof v === "string" ? v : undefined}>
                    {v}
                  </div>
                </div>
              ))}
            </div>

            {(fields.type || fields.colour || fields.cost || fields.power) && (
              <div className="mt-3 space-y-1.5 text-[12.5px]" style={{ color: PAGE.panelText2 }}>
                {fields.type ? (
                  <p>
                    <span style={{ color: PAGE.panelText3 }}>Type </span>
                    {fields.type}
                  </p>
                ) : null}
                {fields.colour ? (
                  <p>
                    <span style={{ color: PAGE.panelText3 }}>Colour </span>
                    {fields.colour}
                  </p>
                ) : null}
                {fields.cost ? (
                  <p>
                    <span style={{ color: PAGE.panelText3 }}>Cost </span>
                    {fields.cost}
                  </p>
                ) : null}
                {fields.power ? (
                  <p>
                    <span style={{ color: PAGE.panelText3 }}>Power </span>
                    {fields.power}
                  </p>
                ) : null}
              </div>
            )}

            {card.source ? (
              <p className="mt-3 text-[11px]" style={{ color: PAGE.panelText3 }}>
                Source · {card.source}
              </p>
            ) : null}

            {!hasPricing || card.price_status === "pending" ? (
              <p
                className="mt-3 rounded-lg border px-3 py-2 text-[12px] leading-snug"
                style={{
                  borderColor: PAGE.panelBorder,
                  background: PAGE.panel2,
                  color: PAGE.panelGold,
                }}
              >
                Price pending — live pricing unavailable until marketplace comps connect.
              </p>
            ) : null}
          </aside>

          {/* Main column */}
          <div className="flex flex-col gap-[18px]">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <div
                  className="text-[11px] font-bold uppercase tracking-[0.14em]"
                  style={{ color: PAGE.accent }}
                >
                  {[card.game, setLabel].filter(Boolean).join(" · ")}
                </div>
                <h1 className="mt-1 text-[clamp(28px,4vw,32px)] font-extrabold tracking-[-0.02em]">
                  {card.name}
                </h1>
                <p className="mt-1 text-[13.5px]" style={{ color: PAGE.text2 }}>
                  {[card.rarity, number ? `#${number}` : null].filter(Boolean).join(" · ") ||
                    "Catalogue card"}
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {card.rarity ? (
                    <span
                      className="whitespace-nowrap rounded-[9px] border px-3.5 py-1.5 text-[12.5px] font-semibold"
                      style={{
                        borderColor: PAGE.border,
                        background: PAGE.surface,
                        color: PAGE.text,
                      }}
                    >
                      {card.rarity}
                    </span>
                  ) : null}
                  {fields.type ? (
                    <span
                      className="whitespace-nowrap rounded-[9px] border px-3.5 py-1.5 text-[12.5px] font-semibold"
                      style={{
                        borderColor: PAGE.accent,
                        background: PAGE.accentSoft,
                        color: PAGE.accent,
                      }}
                    >
                      {fields.type}
                    </span>
                  ) : null}
                </div>
              </div>
              <div className="text-right sm:mr-[40px] lg:mr-[60px]">
                <div className="text-[30px] font-extrabold tabular-nums leading-none">
                  {displayPrice != null ? <Money usd={displayPrice} /> : "—"}
                </div>
                <div
                  className="mt-1 text-[13px] font-bold"
                  style={{ color: hasPricing ? PAGE.up : PAGE.text3 }}
                >
                  {hasPricing ? (
                    <>
                      30d median · <Num n={summary.count} /> sales
                    </>
                  ) : (
                    "Price pending"
                  )}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3.5 sm:grid-cols-4">
              <div>
                <div className="text-xs" style={{ color: PAGE.text3 }}>
                  Last Sold Price
                </div>
                <div className="mt-0.5 text-base font-bold tabular-nums">
                  {comps[0] ? (
                    new Intl.NumberFormat(undefined, {
                      style: "currency",
                      currency: comps[0].currency,
                    }).format(comps[0].price)
                  ) : displayPrice != null ? (
                    <Money usd={displayPrice} />
                  ) : (
                    "—"
                  )}
                </div>
              </div>
              <div>
                <div className="text-xs" style={{ color: PAGE.text3 }}>
                  Last Sold Date
                </div>
                <div className="mt-0.5 text-base font-bold tabular-nums">
                  {formatSoldAgo(lastSold)}
                </div>
              </div>
              <div>
                <div className="text-xs" style={{ color: PAGE.text3 }}>
                  Pop
                </div>
                <div className="mt-0.5 text-base font-bold tabular-nums">
                  {population && population.total > 0 ? <Num n={population.total} /> : "—"}
                </div>
              </div>
              <div>
                <div className="text-xs" style={{ color: PAGE.text3 }}>
                  30d range
                </div>
                <div className="mt-0.5 text-base font-bold tabular-nums">
                  {hasPricing ? (
                    <>
                      <Money usd={summary.min_usd} /> – <Money usd={summary.max_usd} />
                    </>
                  ) : (
                    "—"
                  )}
                </div>
              </div>
            </div>

            {fields.effect ? (
              <div
                className="rounded-[18px] border px-4 py-3.5 text-sm leading-relaxed shadow-[0_1px_2px_rgba(23,24,28,0.05)]"
                style={{
                  background: PAGE.surface,
                  borderColor: PAGE.border,
                  color: PAGE.text2,
                }}
              >
                <div
                  className="text-[11px] font-bold uppercase tracking-[0.1em]"
                  style={{ color: PAGE.accent }}
                >
                  Effect
                </div>
                <p className="mt-1.5 whitespace-pre-wrap">{fields.effect}</p>
              </div>
            ) : null}

            <div
              className="rounded-[18px] border p-[18px] shadow-[0_1px_2px_rgba(23,24,28,0.05)]"
              style={{ background: PAGE.surface, borderColor: PAGE.border }}
            >
              <div className="mb-3.5 flex items-center justify-between gap-3">
                <div className="text-[15px] font-bold">Price history</div>
                <span className="text-xs" style={{ color: PAGE.text3 }}>
                  Last 90 days
                </span>
              </div>
              <PriceChart data={chart} accent={PAGE.accent} />
            </div>

            <div
              className="rounded-[18px] border p-[18px] shadow-[0_1px_2px_rgba(23,24,28,0.05)]"
              style={{
                background: PAGE.surface,
                borderColor: PAGE.border,
              }}
            >
              <MarketplacePrices cardId={card.id} initial={sources} tone="daylight" />
            </div>

            {population && population.total > 0 ? (
              <div className="flex flex-wrap gap-2">
                {population.entries.map((e) => (
                  <span
                    key={`${e.grade_company}-${e.grade}`}
                    className="whitespace-nowrap rounded-md border px-2 py-1 text-xs"
                    style={{
                      borderColor: PAGE.border,
                      background: PAGE.surface,
                      color: PAGE.text2,
                    }}
                  >
                    {e.grade_company} {e.grade}:{" "}
                    <span className="font-semibold" style={{ color: PAGE.text }}>
                      <Num n={e.pop_count} />
                    </span>
                  </span>
                ))}
                <a
                  href={popReportUrl(card)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs font-semibold hover:underline"
                  style={{ color: PAGE.accent }}
                >
                  PSA pop report →
                </a>
              </div>
            ) : (
              <a
                href={popReportUrl(card)}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm font-semibold hover:underline"
                style={{ color: PAGE.accent }}
              >
                PSA pop report →
              </a>
            )}

            <div>
              <CardActions
                cardId={card.id}
                cardName={card.name}
                medianUsd={summary.median_usd}
              />
            </div>

            <div
              className="rounded-[18px] border p-[18px] shadow-[0_1px_2px_rgba(23,24,28,0.05)]"
              style={{
                background: PAGE.panel,
                borderColor: PAGE.panelBorder,
                color: PAGE.panelText,
              }}
            >
              <div className="mb-3.5 flex items-center justify-between gap-3">
                <div className="text-[15px] font-bold">Recent sold prices</div>
                <span className="text-xs" style={{ color: PAGE.panelText3 }}>
                  Last 90 days · {comps.length} sales
                </span>
              </div>
              <CompsTable comps={comps} tone="panel" />
            </div>

            <div
              className="rounded-[18px] border p-[18px] shadow-[0_1px_2px_rgba(23,24,28,0.05)]"
              style={{
                background: PAGE.panel,
                borderColor: PAGE.panelBorder,
                color: PAGE.panelText,
              }}
            >
              <div className="mb-3.5 flex items-center justify-between gap-3">
                <div className="text-[15px] font-bold">Active listings</div>
                <span className="text-xs" style={{ color: PAGE.panelText3 }}>
                  {listings.length > 0 ? `${listings.length} live` : "None yet"}
                </span>
              </div>
              {listings.length === 0 ? (
                <p className="text-sm" style={{ color: PAGE.panelText2 }}>
                  Live listings pending marketplace source approval.
                </p>
              ) : (
                <ListingsTable listings={listings} tone="panel" />
              )}
            </div>

            {roi ? <AiVerdict verdict={roi} /> : null}
          </div>
        </div>
      </div>
    </main>
  );
}
