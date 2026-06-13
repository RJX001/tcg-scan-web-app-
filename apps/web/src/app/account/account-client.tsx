"use client";

import { Button, Card, CardContent, CardHeader, CardTitle } from "@tcgscan/ui";
import { getAccount, openBillingPortal, startCheckout, updateAccountPreferences } from "@tcgscan/sdk-ts";
import { useCallback, useEffect, useState } from "react";

export function AccountClient() {
  const [account, setAccount] = useState<Awaited<ReturnType<typeof getAccount>> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [savingPrefs, setSavingPrefs] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setAccount(await getAccount());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load account");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function upgrade() {
    try {
      const { url } = await startCheckout();
      window.location.href = url;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Checkout unavailable — configure Stripe keys");
    }
  }

  async function manage() {
    try {
      const { url } = await openBillingPortal();
      window.location.href = url;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Billing portal unavailable");
    }
  }

  if (loading) return <p className="text-sm text-zinc-500">Loading account…</p>;
  if (error && !account) return <p className="text-sm text-red-600">{error}</p>;
  if (!account) return null;

  const isPro = account.tier === "pro";

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Your plan</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <p>
            Current tier:{" "}
            <span className="font-semibold uppercase">{account.tier}</span>
          </p>
          {!isPro && account.scans_per_day != null && (
            <p className="text-zinc-600">{account.scans_per_day} scans per day on Free</p>
          )}
          {!isPro && account.portfolio_limit != null && (
            <p className="text-zinc-600">Up to {account.portfolio_limit} portfolio cards on Free</p>
          )}
          {isPro ? (
            <Button onClick={() => void manage()}>Manage subscription</Button>
          ) : (
            <Button onClick={() => void upgrade()}>Upgrade to Pro — $9.99/mo</Button>
          )}
          {error && <p className="text-red-600">{error}</p>}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Price comp window</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <p className="text-zinc-600">
            Marketplace averages (eBay, TCGPlayer, Cardmarket) use this lookback on scan results and card
            pages. Free: 30 days.
          </p>
          {isPro ? (
            <label className="flex flex-wrap items-center gap-2">
              <span className="text-zinc-700">Average window</span>
              <select
                value={account.comps_days ?? 30}
                disabled={savingPrefs}
                onChange={(e) => {
                  const comps_days = Number(e.target.value);
                  setSavingPrefs(true);
                  void updateAccountPreferences({ comps_days })
                    .then(setAccount)
                    .catch((err: unknown) => {
                      setError(err instanceof Error ? err.message : "Failed to save preference");
                    })
                    .finally(() => setSavingPrefs(false));
                }}
                className="rounded-lg border border-zinc-300 px-2 py-1"
              >
                <option value={7}>7 days</option>
                <option value={30}>30 days</option>
                <option value={90}>90 days</option>
                <option value={180}>180 days</option>
              </select>
            </label>
          ) : (
            <p className="text-zinc-500">Upgrade to Pro to use 7, 90, or 180-day windows.</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>What Pro unlocks</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="list-inside list-disc space-y-1 text-sm text-zinc-600">
            <li>Unlimited scans</li>
            <li>Unlimited portfolio</li>
            <li>Price alerts</li>
            <li>Custom marketplace comp window (7–180 days)</li>
            <li>Daily market digest (coming soon)</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
