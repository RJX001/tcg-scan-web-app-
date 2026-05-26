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

export async function getListings(cardId: string, limit = 20): Promise<ListingOut[]> {
  return apiFetch<ListingOut[]>(`/v1/cards/${cardId}/listings?limit=${limit}`);
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
