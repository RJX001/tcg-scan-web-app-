"use client";

import { Button, Card, CardContent } from "@tcgscan/ui";
import type { AdminIngestResult, AdminSourceDiagnostic, AdminSourcesStatus, AccountOut } from "@tcgscan/sdk-ts";
import { getAdminSourceTest, getAdminSourcesStatus, getMe, postAdminSourceImport, postAdminSourceIngest } from "@tcgscan/sdk-ts";
import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";

import { isAdminRole } from "@/lib/auth/admin-access";
import { syncApiAuthFromSupabase } from "@/lib/auth/api-session";

type SourceRow = {
  id: string;
  label: string;
  provider: string;
  testSlug: string;
  ingestSlug?: string;
  importSlug?: string;
  group: "catalog" | "pricing" | "trends";
};

const SOURCE_ROWS: SourceRow[] = [
  { id: "pokemon", label: "Pokémon", provider: "pokemontcg.io", testSlug: "pokemon", ingestSlug: "pokemon", importSlug: "pokemon", group: "catalog" },
  { id: "scryfall", label: "MTG / Scryfall", provider: "Scryfall", testSlug: "scryfall", ingestSlug: "scryfall", importSlug: "scryfall", group: "catalog" },
  { id: "yugioh", label: "Yu-Gi-Oh / YGOPRODeck", provider: "YGOPRODeck", testSlug: "ygopro", ingestSlug: "ygopro", importSlug: "ygopro", group: "catalog" },
  { id: "one_piece", label: "One Piece / OPTCG API", provider: "optcgapi", testSlug: "one-piece", ingestSlug: "one-piece", importSlug: "one-piece", group: "catalog" },
  {
    id: "dragon_ball_fw",
    label: "Dragon Ball Fusion World / Bandai",
    provider: "bandai_fusion_world",
    testSlug: "dragon-ball-fusion-world",
    ingestSlug: "dragon-ball-fusion-world",
    group: "catalog",
  },
  {
    id: "dragon_ball_masters",
    label: "Dragon Ball Masters / Bandai",
    provider: "bandai_masters",
    testSlug: "dragon-ball-masters",
    ingestSlug: "dragon-ball-masters",
    group: "catalog",
  },
  { id: "ebay", label: "eBay", provider: "eBay Browse", testSlug: "ebay", ingestSlug: "ebay", group: "pricing" },
  { id: "reddit", label: "Reddit", provider: "Reddit API", testSlug: "reddit", group: "trends" },
  { id: "cardmarket", label: "Cardmarket / Apify", provider: "Apify", testSlug: "cardmarket", group: "pricing" },
];

type DiagnosticStatus = AdminSourceDiagnostic["status"];

function statusBadge(status: DiagnosticStatus | "unknown" | "idle") {
  const styles: Record<string, string> = {
    success: "bg-emerald-100 text-emerald-800",
    partial: "bg-amber-100 text-amber-900",
    missing_env: "bg-zinc-200 text-zinc-800",
    pending_approval: "bg-sky-100 text-sky-900",
    not_implemented: "bg-zinc-100 text-zinc-700",
    failed: "bg-red-100 text-red-800",
    running: "bg-blue-100 text-blue-900",
    queued: "bg-indigo-100 text-indigo-900",
    unknown: "bg-zinc-100 text-zinc-600",
    idle: "bg-zinc-100 text-zinc-500",
  };
  return (
    <span className={`rounded px-2 py-0.5 text-xs font-semibold uppercase ${styles[status] ?? styles.unknown}`}>
      {status.replaceAll("_", " ")}
    </span>
  );
}

function mapImplementationStatus(implementation: string): DiagnosticStatus {
  if (implementation === "working" || implementation === "connected") return "success";
  if (implementation === "partial") return "partial";
  if (implementation === "pending_approval") return "pending_approval";
  if (implementation === "missing" || implementation === "not_implemented") return "not_implemented";
  return "partial";
}

function isComplianceError(message: string): boolean {
  const lower = message.toLowerCase();
  return (
    lower.includes("compliance") ||
    lower.includes("disabled") ||
    lower.includes("marketplace account deletion") ||
    lower.includes("pending approval")
  );
}

type AccessState = "loading" | "unauthenticated" | "forbidden" | "ready";

export function AdminSourcesClient() {
  const [access, setAccess] = useState<AccessState>("loading");
  const [me, setMe] = useState<AccountOut | null>(null);
  const [statusPayload, setStatusPayload] = useState<AdminSourcesStatus | null>(null);
  const [diagnostics, setDiagnostics] = useState<Record<string, AdminSourceDiagnostic>>({});
  const [testingId, setTestingId] = useState<string | null>(null);
  const [ingestingId, setIngestingId] = useState<string | null>(null);
  const [importingId, setImportingId] = useState<string | null>(null);
  const [ingestResults, setIngestResults] = useState<Record<string, AdminIngestResult>>({});
  const [error, setError] = useState<string | null>(null);

  const statsByKey = useMemo(() => {
    const map = new Map<string, NonNullable<AdminSourcesStatus["catalog_stats"]>[number]>();
    for (const row of statusPayload?.catalog_stats ?? []) {
      map.set(row.source_key, row);
    }
    return map;
  }, [statusPayload]);

  const pricingStatsByKey = useMemo(() => {
    const map = new Map<string, NonNullable<AdminSourcesStatus["pricing_stats"]>[number]>();
    for (const row of statusPayload?.pricing_stats ?? []) {
      map.set(row.source_key, row);
    }
    return map;
  }, [statusPayload]);

  const catalogMetaId = (row: SourceRow) =>
    row.id === "scryfall"
      ? "mtg"
      : row.id === "yugioh"
        ? "yugioh"
        : row.id === "one_piece"
          ? "one_piece"
          : row.id === "dragon_ball_fw"
            ? "dragon_ball_fusion_world"
            : row.id === "dragon_ball_masters"
              ? "dragon_ball_masters"
              : row.id;

  const ingestSourceKey = (row: SourceRow) =>
    row.id === "scryfall"
      ? "scryfall"
      : row.id === "yugioh"
        ? "ygopro"
        : row.id === "one_piece"
          ? "one_piece"
          : row.id === "dragon_ball_fw"
            ? "dragon_ball_fusion_world"
            : row.id === "dragon_ball_masters"
              ? "dragon_ball_masters"
              : row.id;

  const catalogById = useMemo(() => {
    const map = new Map<string, AdminSourcesStatus["catalog_sources"][number]>();
    for (const row of statusPayload?.catalog_sources ?? []) {
      map.set(row.id, row);
    }
    return map;
  }, [statusPayload]);

  const pricingById = useMemo(() => {
    const map = new Map<string, AdminSourcesStatus["pricing_sources"][number]>();
    for (const row of statusPayload?.pricing_sources ?? []) {
      map.set(row.id, row);
    }
    return map;
  }, [statusPayload]);

  const load = useCallback(async () => {
    setError(null);
    setAccess("loading");

    const token = await syncApiAuthFromSupabase();
    if (!token) {
      setAccess("unauthenticated");
      window.location.assign("/sign-in?redirectedFrom=%2Fadmin%2Fsources");
      return;
    }

    try {
      const account = await getMe();
      setMe(account);
      if (!isAdminRole(account.role)) {
        setAccess("forbidden");
        return;
      }
      setStatusPayload(await getAdminSourcesStatus());
      setAccess("ready");
    } catch (e) {
      const message = e instanceof Error ? e.message : "Failed to load source diagnostics";
      if (message.includes("API error 401")) {
        setAccess("unauthenticated");
        window.location.assign("/sign-in?redirectedFrom=%2Fadmin%2Fsources");
        return;
      }
      setError(message);
      setAccess("forbidden");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function runTest(row: SourceRow) {
    setTestingId(row.id);
    setError(null);
    try {
      const result = await getAdminSourceTest(row.testSlug);
      setDiagnostics((prev) => ({ ...prev, [row.id]: result }));
    } catch (e) {
      setDiagnostics((prev) => ({
        ...prev,
        [row.id]: {
          status: "failed",
          provider: row.provider,
          message: e instanceof Error ? e.message : "Test request failed",
        },
      }));
    } finally {
      setTestingId(null);
    }
  }

  async function runImport(row: SourceRow) {
    if (!row.importSlug) return;
    setImportingId(row.id);
    setError(null);
    try {
      const result = await postAdminSourceImport(row.importSlug);
      setIngestResults((prev) => ({ ...prev, [row.id]: result }));
      setStatusPayload(await getAdminSourcesStatus());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Import failed");
    } finally {
      setImportingId(null);
    }
  }

  async function runIngest(row: SourceRow) {
    if (!row.ingestSlug) return;
    setIngestingId(row.id);
    setError(null);
    try {
      const result =
        row.id === "ebay"
          ? await postAdminSourceIngest(row.ingestSlug, {
              limit: 25,
              query: "pokemon card charizard",
            })
          : await postAdminSourceIngest(row.ingestSlug, { limit: 100 });
      setIngestResults((prev) => ({ ...prev, [row.id]: result }));
      setStatusPayload(await getAdminSourcesStatus());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ingest failed");
    } finally {
      setIngestingId(null);
    }
  }

  function configuredStatus(row: SourceRow): DiagnosticStatus | "idle" {
    const diag = diagnostics[row.id];
    if (row.id === "ebay") {
      const meta = pricingById.get("ebay");
      if (!meta?.configured) return "missing_env";
      if (diag?.status === "success") return "success";
      if (diag?.status === "failed" && diag.message && isComplianceError(diag.message)) {
        return "pending_approval";
      }
      if (meta.configured) return "success";
      return mapImplementationStatus(meta.implementation);
    }
    if (row.group === "catalog") {
      const meta = catalogById.get(catalogMetaId(row));
      if (!meta) return "idle";
      if (!meta.configured) return "missing_env";
      return mapImplementationStatus(meta.implementation);
    }
    if (row.group === "pricing" || row.group === "trends") {
      const meta = pricingById.get(row.id === "cardmarket" ? "cardmarket" : row.id);
      if (!meta) return "idle";
      if (!meta.configured && row.id !== "reddit") return "missing_env";
      return mapImplementationStatus(meta.implementation);
    }
    return "idle";
  }

  if (access === "loading") {
    return <p className="text-sm text-zinc-500">Loading source diagnostics…</p>;
  }

  if (access === "forbidden") {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="font-semibold text-zinc-900">Admin access required</p>
          <p className="mt-1 text-sm text-zinc-600">
            Current role: <span className="font-mono">{me?.role ?? "unknown"}</span>
          </p>
          {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-zinc-600">
          Live probes call our FastAPI backend only. No external APIs or secrets are exposed in the browser.
        </p>
        <Link href="/admin" className="text-sm font-medium text-zinc-700 underline-offset-2 hover:underline">
          Back to dashboard
        </Link>
      </div>

      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      <Card>
        <CardContent className="pt-6">
          <p className="text-sm text-amber-800">
            Full catalogue imports should run as background jobs. Use &quot;Ingest sample&quot; (limit 100)
            for safe testing only.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="overflow-x-auto pt-6">
          <table className="w-full min-w-[960px] text-left text-sm">
            <thead>
              <tr className="border-b text-xs uppercase text-zinc-500">
                <th className="pb-2 pr-4">Source</th>
                <th className="pb-2 pr-4">Count</th>
                <th className="pb-2 pr-4">Last sample</th>
                <th className="pb-2 pr-4">Last full</th>
                <th className="pb-2 pr-4">Run</th>
                <th className="pb-2 pr-4">Config</th>
                <th className="pb-2 pr-4">Live test</th>
                <th className="pb-2 pr-4">Message</th>
                <th className="pb-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {SOURCE_ROWS.map((row) => {
                const diag = diagnostics[row.id];
                const ingest = ingestResults[row.id];
                const configStatus = configuredStatus(row);
                const stat = statsByKey.get(ingestSourceKey(row));
                const pricingStat = row.id === "ebay" ? pricingStatsByKey.get("ebay") : undefined;
                const countLabel =
                  row.id === "ebay"
                    ? pricingStat?.listing_count != null
                      ? pricingStat.listing_count.toLocaleString()
                      : "—"
                    : stat?.card_count != null
                      ? stat.card_count.toLocaleString()
                      : "—";
                const lastSample =
                  row.id === "ebay"
                    ? pricingStat?.last_success_at
                    : stat?.last_sample_at ?? stat?.last_success_at;
                const lastFull = row.id === "ebay" ? null : stat?.last_full_at;
                const runStatus = row.id === "ebay" ? null : stat?.current_run_status;
                return (
                  <tr key={row.id} className="border-b border-zinc-100 align-top">
                    <td className="py-3 pr-4">
                      <p className="font-medium">{row.label}</p>
                      <p className="text-xs text-zinc-500">{row.provider}</p>
                    </td>
                    <td className="py-3 pr-4 tabular-nums">{countLabel}</td>
                    <td className="py-3 pr-4 text-xs text-zinc-600">
                      {lastSample ? new Date(lastSample).toLocaleString() : "Never"}
                    </td>
                    <td className="py-3 pr-4 text-xs text-zinc-600">
                      {row.id === "ebay" ? "—" : lastFull ? new Date(lastFull).toLocaleString() : "Never"}
                    </td>
                    <td className="py-3 pr-4 text-xs text-zinc-600">
                      {runStatus ? statusBadge(runStatus as DiagnosticStatus) : "—"}
                    </td>
                    <td className="py-3 pr-4">{statusBadge(configStatus)}</td>
                    <td className="py-3 pr-4">
                      {diag ? statusBadge(diag.status) : statusBadge("idle")}
                    </td>
                    <td className="py-3 pr-4 text-zinc-600">
                      {diag ? (
                        <div className="space-y-1">
                          <p>{diag.message}</p>
                          {row.id === "ebay" ? (
                            <p className="text-xs text-zinc-500">
                              Connected for Browse API. Listing ingest optional.
                            </p>
                          ) : null}
                          {diag.sample_card_name ? (
                            <p className="text-xs">
                              Sample: {diag.sample_card_name}
                              {diag.sample_card_id ? ` (${diag.sample_card_id})` : ""}
                            </p>
                          ) : null}
                          {diag.set_count != null ? (
                            <p className="text-xs">Sets: {diag.set_count}</p>
                          ) : null}
                          {ingest ? (
                            <p className="text-xs text-emerald-700">
                              Ingest: +{ingest.inserted_count} / ~{ingest.updated_count} updated ·{" "}
                              {ingest.message}
                            </p>
                          ) : null}
                        </div>
                      ) : (
                        <span className="text-xs text-zinc-400">Run test to probe live connectivity</span>
                      )}
                    </td>
                    <td className="py-3">
                      <div className="flex flex-wrap gap-1">
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={testingId === row.id}
                          onClick={() => void runTest(row)}
                        >
                          {testingId === row.id ? "Testing…" : "Test"}
                        </Button>
                        {row.ingestSlug ? (
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={ingestingId === row.id}
                            onClick={() => void runIngest(row)}
                          >
                            {ingestingId === row.id ? "Ingesting…" : "Ingest sample"}
                          </Button>
                        ) : null}
                        {row.importSlug ? (
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={importingId === row.id}
                            onClick={() => void runImport(row)}
                          >
                            {importingId === row.id ? "Importing…" : "Import full"}
                          </Button>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}
