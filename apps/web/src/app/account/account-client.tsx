"use client";

import { Button, Card, CardContent, CardHeader, CardTitle } from "@tcgscan/ui";
import type { AccountOut } from "@tcgscan/sdk-ts";
import { getAccount, openBillingPortal, startCheckout, updateAccountPreferences } from "@tcgscan/sdk-ts";
import { useCallback, useEffect, useState } from "react";

import { syncApiAuthFromSupabase } from "@/lib/auth/api-session";

function subscriptionStatus(account: AccountOut): string | null {
  const extended = account as AccountOut & { subscription_status?: string | null };
  return extended.subscription_status ?? null;
}

function parseApiError(err: unknown): string {
  if (!(err instanceof Error)) {
    return "Request failed";
  }
  if (err.message.includes("API error 401")) {
    return "Your session expired or the API rejected your sign-in. Try signing out and back in.";
  }
  return err.message;
}

export function AccountClient() {
  const [account, setAccount] = useState<AccountOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [savingPrefs, setSavingPrefs] = useState(false);

  const ensureAuthToken = useCallback(async (): Promise<string | null> => {
    const token = await syncApiAuthFromSupabase();
    if (!token) {
      window.location.assign("/sign-in?redirectedFrom=%2Faccount");
      return null;
    }
    return token;
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const token = await ensureAuthToken();
      if (!token) {
        return;
      }
      setAccount(await getAccount());
    } catch (e) {
      setError(parseApiError(e));
    } finally {
      setLoading(false);
    }
  }, [ensureAuthToken]);

  useEffect(() => {
    void load();
  }, [load]);

  async function upgrade() {
    setError(null);
    try {
      const token = await ensureAuthToken();
      if (!token) {
        return;
      }
      const { url } = await startCheckout();
      window.location.href = url;
    } catch (e) {
      setError(parseApiError(e));
    }
  }

  async function manage() {
    setError(null);
    try {
      const token = await ensureAuthToken();
      if (!token) {
        return;
      }
      const { url } = await openBillingPortal();
      window.location.href = url;
    } catch (e) {
      setError(parseApiError(e));
    }
  }

  if (loading) {
    return <p className="text-sm text-zinc-500">Loading account…</p>;
  }

  if (!account) {
    return (
      <div className="space-y-3">
        {error ? (
          <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
            {error}
          </p>
        ) : (
          <p className="text-sm text-zinc-500">Unable to load account details.</p>
        )}
      </div>
    );
  }

  const isPro = account.tier === "pro";
  const status = subscriptionStatus(account);

  return (
    <div className="space-y-6">
      {error ? (
        <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-900" role="alert">
          {error}
        </p>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Your plan</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          {account.email ? (
            <p>
              Email <span className="font-medium text-zinc-900">{account.email}</span>
            </p>
          ) : null}
          {account.account_number ? (
            <p>
              Account{" "}
              <span className="font-mono font-semibold">#{account.account_number}</span>
            </p>
          ) : null}
          <p>
            Role <span className="font-semibold">{account.role}</span>
          </p>
          <p>
            Current tier{" "}
            <span className="font-semibold uppercase">{account.tier}</span>
          </p>
          {status ? (
            <p>
              Subscription status{" "}
              <span className="font-semibold capitalize">{status.replaceAll("_", " ")}</span>
            </p>
          ) : null}
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
                  setError(null);
                  void ensureAuthToken()
                    .then((token) => {
                      if (!token) {
                        return null;
                      }
                      return updateAccountPreferences({ comps_days });
                    })
                    .then((next) => {
                      if (next) {
                        setAccount(next);
                      }
                    })
                    .catch((err: unknown) => {
                      setError(parseApiError(err));
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
