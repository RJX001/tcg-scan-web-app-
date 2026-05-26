"use client";

import { Button, Card, CardContent, CardHeader, CardTitle } from "@tcgscan/ui";
import { getAccount, openBillingPortal, startCheckout } from "@tcgscan/sdk-ts";
import { useCallback, useEffect, useState } from "react";

export function AccountClient() {
  const [account, setAccount] = useState<Awaited<ReturnType<typeof getAccount>> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

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
          <CardTitle>What Pro unlocks</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="list-inside list-disc space-y-1 text-sm text-zinc-600">
            <li>Unlimited scans</li>
            <li>Unlimited portfolio</li>
            <li>Price alerts</li>
            <li>Daily market digest (coming soon)</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
