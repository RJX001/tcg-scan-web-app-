"use client";

import { getDigestPreview } from "@tcgscan/sdk-ts";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

function extractTopMover(body: string): string | null {
  const m = body.match(
    /\bled by\s+([A-Za-z0-9'’.\-]+(?:\s+[A-Za-z0-9'’.\-]+){0,3})/i,
  );
  if (m) return m[1];
  const alt = body.match(
    /\b([A-Z][A-Za-z0-9'’.\-]+(?:\s+[A-Z][A-Za-z0-9'’.\-]+){0,2})\s+is flagged/i,
  );
  return alt?.[1] ?? null;
}

function extractPortfolioChange(body: string): string | null {
  const up = body.match(/\bup\s+([\d.]+%)/i);
  if (up) return `▲ ${up[1]}`;
  const down = body.match(/\bdown\s+([\d.]+%)/i);
  if (down) return `▼ ${down[1]}`;
  return null;
}

function countVerdictMentions(body: string): number {
  const buys = (body.match(/\bBuy\b/gi) ?? []).length;
  const sells = (body.match(/\bSell\b/gi) ?? []).length;
  return buys + sells;
}

export function InsightsClient() {
  const [digest, setDigest] = useState<Awaited<ReturnType<typeof getDigestPreview>> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setDigest(await getDigestPreview());
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to load digest";
      setError(
        msg.includes("403") || msg.includes("Pro")
          ? "Daily digest is a Pro feature — upgrade at /account"
          : msg,
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const stamp = new Date().toLocaleString(undefined, {
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });

  if (loading) {
    return <p className="text-sm" style={{ color: "#5B5F68" }}>Generating your morning summary…</p>;
  }

  const body = digest?.body ?? "";
  const pfChange = extractPortfolioChange(body);
  const verdicts = countVerdictMentions(body);
  const topMover = extractTopMover(body);

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-4 pb-2">
        <div>
          <h1
            className="text-[32px] font-extrabold tracking-[-0.02em]"
            style={{ fontFamily: "var(--font-display), Georgia, serif", color: "#17181C" }}
          >
            Insights
          </h1>
          <p className="mt-1 text-[14.5px]" style={{ color: "#5B5F68" }}>
            Your morning market summary — portfolio movers, trending cards and opportunities.
          </p>
        </div>
        <span
          className="rounded-full px-3 py-1.5 text-[11px] font-bold uppercase tracking-[0.1em]"
          style={{ background: "rgba(182,134,46,0.10)", color: "#B6862E" }}
        >
          Pro
        </span>
      </div>

      {error && (
        <div
          className="mt-3 rounded-[18px] border px-5 py-4 text-sm"
          style={{ background: "#FFFFFF", borderColor: "#E4E1D8", color: "#5B5F68" }}
        >
          {error}{" "}
          <Link href="/account" className="font-semibold underline" style={{ color: "#B6862E" }}>
            View plans
          </Link>
        </div>
      )}

      {digest && (
        <div
          className="mt-3 rounded-[18px] border p-6 shadow-[0_1px_2px_rgba(23,24,28,0.05)]"
          style={{ background: "#1E2128", borderColor: "#2A2E37", color: "#F6F7F9" }}
        >
          <div
            className="text-[11px] font-bold uppercase tracking-[0.14em]"
            style={{ color: "#E0B94A" }}
          >
            {stamp}
          </div>
          {digest.subject && (
            <h2
              className="mt-3 text-lg font-bold"
              style={{ fontFamily: "var(--font-display), Georgia, serif" }}
            >
              {digest.subject}
            </h2>
          )}
          <p className="mt-3 whitespace-pre-wrap text-[15px] leading-[1.65]">{digest.body}</p>

          <div className="mt-5 grid gap-3 sm:grid-cols-3">
            <div
              className="rounded-xl border p-3.5"
              style={{ background: "#252932", borderColor: "#2A2E37" }}
            >
              <div className="text-[11px] uppercase tracking-[0.06em]" style={{ color: "#8C93A1" }}>
                Portfolio
              </div>
              <div
                className="mt-1 text-lg font-extrabold"
                style={{
                  color: pfChange?.startsWith("▼") ? "#FF6B70" : "#34D499",
                  fontFamily: "var(--font-mono), monospace",
                }}
              >
                {pfChange ?? `${digest.portfolio_count} cards`}
              </div>
            </div>
            <div
              className="rounded-xl border p-3.5"
              style={{ background: "#252932", borderColor: "#2A2E37" }}
            >
              <div className="text-[11px] uppercase tracking-[0.06em]" style={{ color: "#8C93A1" }}>
                Verdicts to act on
              </div>
              <div
                className="mt-1 text-lg font-extrabold"
                style={{ fontFamily: "var(--font-mono), monospace" }}
              >
                {verdicts > 0 ? verdicts : "—"}
              </div>
            </div>
            <div
              className="rounded-xl border p-3.5"
              style={{ background: "#252932", borderColor: "#2A2E37" }}
            >
              <div className="text-[11px] uppercase tracking-[0.06em]" style={{ color: "#8C93A1" }}>
                Top mover
              </div>
              <div
                className="mt-1 truncate text-lg font-extrabold"
                style={{ fontFamily: "var(--font-display), Georgia, serif" }}
              >
                {topMover ?? "—"}
              </div>
            </div>
          </div>

          <div className="mt-5 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => void load()}
              className="rounded-[10px] border px-3.5 py-2 text-[13px] font-semibold"
              style={{ borderColor: "#2A2E37", background: "#252932", color: "#F6F7F9" }}
            >
              Refresh
            </button>
            <Link
              href="/portfolio"
              className="rounded-[10px] px-3.5 py-2 text-[13px] font-bold"
              style={{ background: "#E0B94A", color: "#1A1408" }}
            >
              View vault
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
