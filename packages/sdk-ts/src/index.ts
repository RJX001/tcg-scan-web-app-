export type HealthResponse = { status: "ok" | "degraded"; version?: string };

export type ScanMatch = {
  card_id: string;
  slug?: string | null;
  name?: string | null;
  game?: string | null;
  set_code?: string | null;
  number?: string | null;
  score: number;
  cos_sim: number;
  ocr_boost?: number;
  popularity_boost?: number;
};

export type DetectBBox = {
  x: number;
  y: number;
  w: number;
  h: number;
  angle?: number;
};

export type ConditionEstimate = {
  overall?: number | null;
  centering?: number | null;
  corners?: number | null;
  edges?: number | null;
  surface?: number | null;
  psa_low?: number | null;
  psa_high?: number | null;
  psa_label?: string | null;
  confidence?: number | null;
  model?: string | null;
  verdict?: GradeVerdict | null;
};

export type GradeVerdict = {
  action: "HOLD" | "SELL" | "GRADE" | "BUY";
  reason: string;
  raw_median_usd?: number | null;
  graded_estimate_usd?: number | null;
  expected_profit_usd?: number | null;
  grading_cost_usd?: number;
};

export type ScanResult = {
  matches: ScanMatch[];
  condition: ConditionEstimate;
  cached?: boolean;
  bbox?: DetectBBox | null;
  stages_ms?: Record<string, number> | null;
};

export type CardOut = {
  id: string;
  slug: string;
  game: string;
  name: string;
  set_code?: string | null;
  set_name?: string | null;
  number?: string | null;
  rarity?: string | null;
  image_urls?: Record<string, unknown> | null;
};

export type CompOut = {
  source: string;
  kind: string;
  sold_at: string;
  price: number;
  currency: string;
  grade?: string | null;
  listing_url?: string | null;
  market_region: string;
};

export type CompSummary = {
  count: number;
  mean_usd?: number | null;
  median_usd?: number | null;
  min_usd?: number | null;
  max_usd?: number | null;
};

export type ChartPoint = {
  day: string;
  median_usd: number;
  sample_count: number;
};

export type SourcePrices = {
  ebay_median_usd?: number | null;
  tcgplayer_median_usd?: number | null;
  cardmarket_median_usd?: number | null;
};

export type PortfolioItemOut = {
  id: string;
  card: CardOut;
  quantity: number;
  cost_basis_usd?: number | null;
  notes?: string | null;
  estimated_value_usd?: number | null;
};

export type AlertOut = {
  id: string;
  card: CardOut;
  direction: "below" | "above";
  threshold_usd: number;
  grade_filter?: string | null;
  active: boolean;
};

export type ListingOut = {
  source: string;
  price: number;
  currency: string;
  grade?: string | null;
  listing_url?: string | null;
  listed_at: string;
  market_region: string;
};

export type PortfolioSummaryOut = {
  item_count: number;
  total_quantity: number;
  total_cost_basis_usd?: number | null;
  estimated_value_usd?: number | null;
};

export type AccountOut = {
  clerk_id: string;
  email?: string | null;
  tier: string;
  portfolio_limit?: number | null;
  scans_per_day?: number | null;
};

const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function devHeaders(): HeadersInit {
  return { "X-Dev-User-Id": "dev-user" };
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${baseUrl}${path}`, {
    ...init,
    headers: { ...devHeaders(), ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`API error ${res.status}: ${detail}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export async function getHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/v1/health");
}

export async function scanCard(
  file: File | Blob,
  opts?: { game?: string; topK?: number },
): Promise<ScanResult> {
  const form = new FormData();
  form.append("image", file);
  if (opts?.game) form.append("game", opts.game);
  if (opts?.topK) form.append("top_k", String(opts.topK));
  return apiFetch<ScanResult>("/v1/scan", { method: "POST", body: form });
}

export async function searchCards(
  q: string,
  opts?: { game?: string; limit?: number },
): Promise<CardOut[]> {
  const params = new URLSearchParams({ q });
  if (opts?.game) params.set("game", opts.game);
  if (opts?.limit) params.set("limit", String(opts.limit));
  return apiFetch<CardOut[]>(`/v1/cards/search?${params}`);
}

export async function getCard(cardId: string): Promise<CardOut> {
  return apiFetch<CardOut>(`/v1/cards/${cardId}`);
}

export async function getCardBySlug(slug: string): Promise<CardOut> {
  return apiFetch<CardOut>(`/v1/cards/slug/${encodeURIComponent(slug)}`);
}

export async function getComps(
  cardId: string,
  days = 30,
  opts?: { source?: string; grade?: string },
): Promise<CompOut[]> {
  const params = new URLSearchParams({ days: String(days) });
  if (opts?.source) params.set("source", opts.source);
  if (opts?.grade) params.set("grade", opts.grade);
  return apiFetch<CompOut[]>(`/v1/cards/${cardId}/comps?${params}`);
}

export async function getCompSummary(cardId: string, days = 30): Promise<CompSummary> {
  return apiFetch<CompSummary>(`/v1/cards/${cardId}/comps/summary?days=${days}`);
}

export async function getChart(cardId: string, days = 90): Promise<ChartPoint[]> {
  return apiFetch<ChartPoint[]>(`/v1/cards/${cardId}/chart?days=${days}`);
}

export async function getSourcePrices(cardId: string, days = 30): Promise<SourcePrices> {
  return apiFetch<SourcePrices>(`/v1/cards/${cardId}/sources?days=${days}`);
}

export async function getGradeRoi(cardId: string, psaHigh = 9): Promise<GradeVerdict> {
  return apiFetch<GradeVerdict>(`/v1/cards/${cardId}/grade-roi?psa_high=${psaHigh}`);
}

export async function getPortfolio(): Promise<PortfolioItemOut[]> {
  return apiFetch<PortfolioItemOut[]>("/v1/portfolio");
}

export async function addToPortfolio(body: {
  card_id: string;
  quantity?: number;
  cost_basis_usd?: number;
  notes?: string;
}): Promise<PortfolioItemOut> {
  return apiFetch<PortfolioItemOut>("/v1/portfolio", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function removeFromPortfolio(itemId: string): Promise<void> {
  await apiFetch<void>(`/v1/portfolio/${itemId}`, { method: "DELETE" });
}

export async function getAlerts(): Promise<AlertOut[]> {
  return apiFetch<AlertOut[]>("/v1/alerts");
}

export async function createAlert(body: {
  card_id: string;
  direction: "below" | "above";
  threshold_usd: number;
  grade_filter?: string;
}): Promise<AlertOut> {
  return apiFetch<AlertOut>("/v1/alerts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function getListings(
  cardId: string,
  limit = 20,
  opts?: { source?: string; grade?: string },
): Promise<ListingOut[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (opts?.source) params.set("source", opts.source);
  if (opts?.grade) params.set("grade", opts.grade);
  return apiFetch<ListingOut[]>(`/v1/cards/${cardId}/listings?${params}`);
}

export async function getPortfolioSummary(): Promise<PortfolioSummaryOut> {
  return apiFetch<PortfolioSummaryOut>("/v1/portfolio/summary");
}

export async function getAccount(): Promise<AccountOut> {
  return apiFetch<AccountOut>("/v1/account");
}

export async function startCheckout(): Promise<{ url: string }> {
  return apiFetch<{ url: string }>("/v1/billing/checkout", { method: "POST" });
}

export async function openBillingPortal(): Promise<{ url: string }> {
  return apiFetch<{ url: string }>("/v1/billing/portal", { method: "POST" });
}

export async function deleteAlert(alertId: string): Promise<void> {
  await apiFetch<void>(`/v1/alerts/${alertId}`, { method: "DELETE" });
}

export type MarketMoverOut = {
  card: CardOut;
  sales_count: number;
  avg_usd?: number | null;
  change_pct?: number | null;
  last_sold_usd?: number | null;
  last_sold_at?: string | null;
  last_sold_grade?: string | null;
  pop_count?: number | null;
};

export type IndexPoint = {
  day: string;
  index_value: number;
  constituents: number;
};

export type MarketIndexOut = {
  name: string;
  days: number;
  change_pct?: number | null;
  points: IndexPoint[];
};

export type PopulationEntry = {
  grade_company: string;
  grade: string;
  pop_count: number;
  as_of: string;
};

export type PopulationOut = {
  total: number;
  entries: PopulationEntry[];
};

export type SavedSearchParams = {
  game?: string | null;
  q?: string | null;
  sort?: string | null;
  days?: number | null;
  grade?: string | null;
};

export type SavedSearchOut = {
  id: string;
  name: string;
  params: SavedSearchParams;
  created_at: string;
};

export type MarketMoversSort =
  | "change"
  | "change_asc"
  | "price"
  | "volume"
  | "recent"
  | "pop"
  | "market_cap";

export type SaleBrowseOut = {
  card: CardOut;
  source: string;
  price: number;
  currency: string;
  price_usd?: number | null;
  grade?: string | null;
  listing_url?: string | null;
  sold_at: string;
  market_region: string;
};

export type ShopListingOut = {
  card: CardOut;
  source: string;
  price: number;
  currency: string;
  price_usd?: number | null;
  grade?: string | null;
  listing_url?: string | null;
  listed_at: string;
};

export type ShopSort = "recent" | "price_asc" | "price_desc";

export type IndexSummaryOut = {
  key: string;
  name: string;
  change_pct?: number | null;
  latest_value?: number | null;
  constituents: number;
};

export type WatchlistItemOut = {
  id: string;
  card: CardOut;
  median_usd_30d?: number | null;
  created_at: string;
};

export type FxOut = {
  base: string;
  as_of?: string | null;
  /** currency -> value of 1 unit in USD (e.g. GBP: 1.27) */
  rates: Record<string, number>;
};

export async function getMarketMovers(opts?: {
  days?: number;
  game?: string;
  q?: string;
  /** "raw", "graded", or a company prefix: PSA, BGS, CGC, SGC, ACE */
  grade?: string;
  sort?: MarketMoversSort;
  limit?: number;
  offset?: number;
}): Promise<MarketMoverOut[]> {
  const params = new URLSearchParams();
  if (opts?.days) params.set("days", String(opts.days));
  if (opts?.game) params.set("game", opts.game);
  if (opts?.q) params.set("q", opts.q);
  if (opts?.grade) params.set("grade", opts.grade);
  if (opts?.sort) params.set("sort", opts.sort);
  if (opts?.limit) params.set("limit", String(opts.limit));
  if (opts?.offset) params.set("offset", String(opts.offset));
  const qs = params.toString();
  return apiFetch<MarketMoverOut[]>(`/v1/market/movers${qs ? `?${qs}` : ""}`);
}

export async function getShopListings(opts?: {
  game?: string;
  q?: string;
  source?: string;
  grade?: string;
  minPrice?: number;
  maxPrice?: number;
  listedAfter?: string;
  listedBefore?: string;
  sort?: ShopSort;
  limit?: number;
  offset?: number;
}): Promise<ShopListingOut[]> {
  const params = new URLSearchParams();
  if (opts?.game) params.set("game", opts.game);
  if (opts?.q) params.set("q", opts.q);
  if (opts?.source) params.set("source", opts.source);
  if (opts?.grade) params.set("grade", opts.grade);
  if (opts?.minPrice != null) params.set("min_price", String(opts.minPrice));
  if (opts?.maxPrice != null) params.set("max_price", String(opts.maxPrice));
  if (opts?.listedAfter) params.set("listed_after", opts.listedAfter);
  if (opts?.listedBefore) params.set("listed_before", opts.listedBefore);
  if (opts?.sort) params.set("sort", opts.sort);
  if (opts?.limit) params.set("limit", String(opts.limit));
  if (opts?.offset) params.set("offset", String(opts.offset));
  const qs = params.toString();
  return apiFetch<ShopListingOut[]>(`/v1/market/listings${qs ? `?${qs}` : ""}`);
}

export async function getSalesBrowse(opts?: {
  game?: string;
  q?: string;
  source?: string;
  grade?: string;
  minPrice?: number;
  maxPrice?: number;
  soldAfter?: string;
  soldBefore?: string;
  sort?: ShopSort;
  limit?: number;
  offset?: number;
}): Promise<SaleBrowseOut[]> {
  const params = new URLSearchParams();
  if (opts?.game) params.set("game", opts.game);
  if (opts?.q) params.set("q", opts.q);
  if (opts?.source) params.set("source", opts.source);
  if (opts?.grade) params.set("grade", opts.grade);
  if (opts?.minPrice != null) params.set("min_price", String(opts.minPrice));
  if (opts?.maxPrice != null) params.set("max_price", String(opts.maxPrice));
  if (opts?.soldAfter) params.set("sold_after", opts.soldAfter);
  if (opts?.soldBefore) params.set("sold_before", opts.soldBefore);
  if (opts?.sort) params.set("sort", opts.sort);
  if (opts?.limit) params.set("limit", String(opts.limit));
  if (opts?.offset) params.set("offset", String(opts.offset));
  const qs = params.toString();
  return apiFetch<SaleBrowseOut[]>(`/v1/market/sales${qs ? `?${qs}` : ""}`);
}

export async function getFxRates(): Promise<FxOut> {
  return apiFetch<FxOut>("/v1/market/fx");
}

export async function getIndexes(days = 7): Promise<IndexSummaryOut[]> {
  return apiFetch<IndexSummaryOut[]>(`/v1/market/indexes?days=${days}`);
}

export async function getWatchlist(): Promise<WatchlistItemOut[]> {
  return apiFetch<WatchlistItemOut[]>("/v1/watchlist");
}

export async function addToWatchlist(cardId: string): Promise<WatchlistItemOut> {
  return apiFetch<WatchlistItemOut>("/v1/watchlist", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ card_id: cardId }),
  });
}

export async function removeFromWatchlist(itemId: string): Promise<void> {
  await apiFetch<void>(`/v1/watchlist/${itemId}`, { method: "DELETE" });
}

export async function getMarketIndex(opts?: {
  days?: number;
  game?: string;
}): Promise<MarketIndexOut> {
  const params = new URLSearchParams();
  if (opts?.days) params.set("days", String(opts.days));
  if (opts?.game) params.set("game", opts.game);
  const qs = params.toString();
  return apiFetch<MarketIndexOut>(`/v1/market/index${qs ? `?${qs}` : ""}`);
}

export async function getPopulation(cardId: string): Promise<PopulationOut> {
  return apiFetch<PopulationOut>(`/v1/cards/${cardId}/population`);
}

export async function getSavedSearches(): Promise<SavedSearchOut[]> {
  return apiFetch<SavedSearchOut[]>("/v1/searches");
}

export async function createSavedSearch(body: {
  name: string;
  params: SavedSearchParams;
}): Promise<SavedSearchOut> {
  return apiFetch<SavedSearchOut>("/v1/searches", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function deleteSavedSearch(searchId: string): Promise<void> {
  await apiFetch<void>(`/v1/searches/${searchId}`, { method: "DELETE" });
}

export type DigestPreview = {
  subject: string;
  body: string;
  portfolio_count: number;
};

export async function getDigestPreview(): Promise<DigestPreview> {
  return apiFetch<DigestPreview>("/v1/digest/preview");
}

export async function exportPortfolioCsv(): Promise<Blob> {
  const res = await fetch(`${baseUrl}/v1/portfolio/export`, {
    headers: devHeaders(),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`API error ${res.status}: ${detail}`);
  }
  return res.blob();
}
