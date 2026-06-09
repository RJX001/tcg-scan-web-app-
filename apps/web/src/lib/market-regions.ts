export type MarketRegion = "us" | "uk" | "eu";
export type MarketRegionFilter = "all" | MarketRegion;

export const MARKET_REGION_FILTERS: { id: MarketRegionFilter; label: string }[] = [
  { id: "all", label: "All markets" },
  { id: "us", label: "US sales" },
  { id: "uk", label: "UK sales" },
  { id: "eu", label: "EU sales" },
];

type RegionInput = {
  source: string;
  currency: string;
  listing_url?: string | null;
  market_region?: string | null;
};

export function inferMarketRegion(item: RegionInput): MarketRegion {
  if (item.market_region === "us" || item.market_region === "uk" || item.market_region === "eu") {
    return item.market_region;
  }

  const source = item.source.toLowerCase();
  const currency = item.currency.toUpperCase();
  const url = (item.listing_url ?? "").toLowerCase();

  if (source === "tcgplayer") return "us";
  if (source === "cardmarket") return "eu";
  if (source.includes("ebay_uk") || source === "ebayuk" || source === "ebay-uk") return "uk";
  if (url.includes("ebay.co.uk")) return "uk";
  if (url.includes("cardmarket.")) return "eu";
  if (currency === "GBP") return "uk";
  if (currency === "EUR") return "eu";
  if (source === "ebay" && currency === "USD") return "us";
  if (url.includes("ebay.com")) return "us";
  if (currency === "USD") return "us";
  return "us";
}

export function matchesMarketRegionFilter(
  item: RegionInput,
  filter: MarketRegionFilter,
): boolean {
  if (filter === "all") return true;
  return inferMarketRegion(item) === filter;
}
