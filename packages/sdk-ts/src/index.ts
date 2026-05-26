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

const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${baseUrl}${path}`, init);
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`API error ${res.status}: ${detail}`);
  }
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

export async function getCard(cardId: string): Promise<CardOut> {
  return apiFetch<CardOut>(`/v1/cards/${cardId}`);
}

export async function getCardBySlug(slug: string): Promise<CardOut> {
  return apiFetch<CardOut>(`/v1/cards/slug/${encodeURIComponent(slug)}`);
}

export async function getComps(cardId: string, days = 30): Promise<CompOut[]> {
  return apiFetch<CompOut[]>(`/v1/cards/${cardId}/comps?days=${days}`);
}

export async function getCompSummary(cardId: string, days = 30): Promise<CompSummary> {
  return apiFetch<CompSummary>(`/v1/cards/${cardId}/comps/summary?days=${days}`);
}
