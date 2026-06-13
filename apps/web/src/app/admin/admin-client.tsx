"use client";

import { Button, Card, CardContent, CardHeader, CardTitle } from "@tcgscan/ui";
import type {
  AdminDataHealthRow,
  AdminOverview,
  AdminRevenue,
  AdminSystem,
  AdminUserRow,
  AccountOut,
} from "@tcgscan/sdk-ts";
import {
  getAdminDataHealth,
  getAdminOverview,
  getAdminRevenue,
  getAdminSystem,
  getAdminUsers,
  getMe,
  setUserAccountNumber,
  setUserRole,
  setUserTier,
} from "@tcgscan/sdk-ts";
import { useCallback, useEffect, useState } from "react";

const ADMIN_ROLES = new Set(["admin", "admin_senior", "owner"]);
const SENIOR_ROLES = new Set(["admin_senior", "owner"]);

function statusBadge(status: AdminDataHealthRow["status"]) {
  const styles = {
    ok: "bg-emerald-100 text-emerald-800",
    stale: "bg-amber-100 text-amber-900",
    down: "bg-red-100 text-red-800",
  };
  return (
    <span className={`rounded px-2 py-0.5 text-xs font-semibold uppercase ${styles[status]}`}>
      {status}
    </span>
  );
}

function Dot({ ok }: { ok: boolean }) {
  return (
    <span
      className={`inline-block h-2.5 w-2.5 rounded-full ${ok ? "bg-emerald-500" : "bg-red-500"}`}
      aria-hidden
    />
  );
}

function KpiCard({ label, value }: { label: string; value: string | number }) {
  return (
    <Card>
      <CardContent className="pt-6">
        <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">{label}</p>
        <p className="mt-1 text-2xl font-bold tabular-nums">{value}</p>
      </CardContent>
    </Card>
  );
}

export function AdminClient() {
  const [me, setMe] = useState<AccountOut | null>(null);
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [dataHealth, setDataHealth] = useState<AdminDataHealthRow[]>([]);
  const [system, setSystem] = useState<AdminSystem | null>(null);
  const [revenue, setRevenue] = useState<AdminRevenue | null>(null);
  const [users, setUsers] = useState<AdminUserRow[]>([]);
  const [userTotal, setUserTotal] = useState(0);
  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionMsg, setActionMsg] = useState<string | null>(null);

  const loadUsers = useCallback(async (q?: string) => {
    const page = await getAdminUsers({ limit: 25, offset: 0, q: q || undefined });
    setUsers(page.items);
    setUserTotal(page.total);
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const account = await getMe();
      setMe(account);
      if (!ADMIN_ROLES.has(account.role ?? "user")) {
        return;
      }
      const [ov, dh, sys] = await Promise.all([
        getAdminOverview(),
        getAdminDataHealth(),
        getAdminSystem(),
      ]);
      setOverview(ov);
      setDataHealth(dh);
      setSystem(sys);
      if (SENIOR_ROLES.has(account.role ?? "user")) {
        setRevenue(await getAdminRevenue());
      }
      await loadUsers();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load admin dashboard");
    } finally {
      setLoading(false);
    }
  }, [loadUsers]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleCompPro(userId: string) {
    setActionMsg(null);
    try {
      await setUserTier(userId, "pro");
      setActionMsg("Tier updated to Pro.");
      await loadUsers(query);
    } catch (e) {
      setActionMsg(e instanceof Error ? e.message : "Failed to update tier");
    }
  }

  async function handleSetRole(userId: string, role: string) {
    setActionMsg(null);
    try {
      await setUserRole(userId, role);
      setActionMsg(`Role set to ${role}.`);
      await loadUsers(query);
    } catch (e) {
      setActionMsg(e instanceof Error ? e.message : "Failed to update role");
    }
  }

  async function handleSetAccountNumber(userId: string) {
    const raw = window.prompt("New account number (1–16 chars):");
    if (!raw) return;
    setActionMsg(null);
    try {
      await setUserAccountNumber(userId, raw.trim());
      setActionMsg(`Account number set to #${raw.trim()}.`);
      await loadUsers(query);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to update account number";
      setActionMsg(msg.includes("409") ? "That number is in use." : msg);
    }
  }

  if (loading) {
    return <p className="text-sm text-zinc-500">Loading admin dashboard…</p>;
  }

  if (!me || !ADMIN_ROLES.has(me.role ?? "user")) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="font-semibold text-zinc-900">Not authorised</p>
          <p className="mt-1 text-sm text-zinc-600">This area is restricted to admin roles.</p>
        </CardContent>
      </Card>
    );
  }

  const isSenior = SENIOR_ROLES.has(me.role ?? "user");
  const isOwner = me.role === "owner";

  return (
    <div className="space-y-8">
      {error && <p className="text-sm text-red-600">{error}</p>}
      {actionMsg && <p className="text-sm text-emerald-700">{actionMsg}</p>}

      {overview && (
        <section>
          <h2 className="mb-3 text-lg font-semibold">Overview</h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <KpiCard label="Total users" value={overview.total_users} />
            <KpiCard label="Pro users" value={overview.pro_users} />
            {isSenior && revenue && (
              <KpiCard label="MRR (est.)" value={`$${revenue.mrr_usd.toFixed(2)}`} />
            )}
            <KpiCard label="Sale events (24h)" value={overview.sale_events_24h} />
            <KpiCard label="New users (24h)" value={overview.new_users_24h} />
            <KpiCard label="New users (7d)" value={overview.new_users_7d} />
            <KpiCard label="Catalog cards" value={overview.cards_in_catalogue} />
            <KpiCard label="Portfolio items" value={overview.total_portfolio_items} />
          </div>
        </section>
      )}

      <section>
        <h2 className="mb-3 text-lg font-semibold">Data health</h2>
        <Card>
          <CardContent className="overflow-x-auto pt-6">
            <table className="w-full min-w-[480px] text-left text-sm">
              <thead>
                <tr className="border-b text-xs uppercase text-zinc-500">
                  <th className="pb-2 pr-4">Source</th>
                  <th className="pb-2 pr-4">Rows</th>
                  <th className="pb-2 pr-4">Last ingest</th>
                  <th className="pb-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {dataHealth.map((row) => (
                  <tr key={row.source} className="border-b border-zinc-100">
                    <td className="py-2 pr-4 font-medium uppercase">{row.source}</td>
                    <td className="py-2 pr-4 tabular-nums">{row.row_count.toLocaleString()}</td>
                    <td className="py-2 pr-4 text-zinc-600">
                      {row.last_ingested_at
                        ? new Date(row.last_ingested_at).toLocaleString()
                        : "—"}
                    </td>
                    <td className="py-2">{statusBadge(row.status)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      </section>

      {system && (
        <section>
          <h2 className="mb-3 text-lg font-semibold">System health</h2>
          <Card>
            <CardContent className="flex flex-wrap gap-6 pt-6 text-sm">
              <p className="flex items-center gap-2">
                <Dot ok={system.db_reachable} /> Database
              </p>
              <p className="flex items-center gap-2">
                <Dot ok={system.redis_reachable} /> Redis
              </p>
              <p className="flex items-center gap-2">
                <Dot ok={system.qdrant_reachable} /> Qdrant
              </p>
              <p className="text-zinc-600">
                API v{system.api_version} · uptime {Math.floor(system.uptime_seconds / 60)}m
              </p>
            </CardContent>
          </Card>
        </section>
      )}

      {isSenior && revenue && (
        <section>
          <h2 className="mb-3 text-lg font-semibold">Revenue</h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <KpiCard label="MRR" value={`$${revenue.mrr_usd.toFixed(2)}`} />
            <KpiCard label="Active Pro" value={revenue.active_pro_count} />
            <KpiCard label="New Pro (30d)" value={revenue.new_subs_30d} />
            <KpiCard label="Churn (30d)" value={revenue.churn_30d} />
          </div>
        </section>
      )}

      <section>
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-semibold">Users ({userTotal})</h2>
          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              void loadUsers(query);
            }}
          >
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search email or account #"
              className="rounded-lg border border-zinc-200 px-3 py-1.5 text-sm"
            />
            <Button type="submit" size="sm" variant="outline">
              Search
            </Button>
          </form>
        </div>
        <Card>
          <CardContent className="overflow-x-auto pt-6">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead>
                <tr className="border-b text-xs uppercase text-zinc-500">
                  <th className="pb-2 pr-3">Account</th>
                  <th className="pb-2 pr-3">Email</th>
                  <th className="pb-2 pr-3">Tier</th>
                  <th className="pb-2 pr-3">Role</th>
                  <th className="pb-2 pr-3">Portfolio</th>
                  <th className="pb-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} className="border-b border-zinc-100">
                    <td className="py-2 pr-3 font-mono text-xs">#{u.account_number}</td>
                    <td className="py-2 pr-3 text-zinc-700">{u.email ?? "—"}</td>
                    <td className="py-2 pr-3 uppercase">{u.tier}</td>
                    <td className="py-2 pr-3">{u.role}</td>
                    <td className="py-2 pr-3 tabular-nums">{u.portfolio_count}</td>
                    <td className="py-2">
                      <div className="flex flex-wrap gap-1">
                        {isSenior && u.tier !== "pro" && (
                          <Button size="sm" variant="outline" onClick={() => void handleCompPro(u.id)}>
                            Comp Pro
                          </Button>
                        )}
                        {isOwner && (
                          <>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => void handleSetRole(u.id, "admin")}
                            >
                              Make admin
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => void handleSetAccountNumber(u.id)}
                            >
                              Edit #
                            </Button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
