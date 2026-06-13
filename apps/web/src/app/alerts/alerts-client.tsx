"use client";

import { Button, Card, CardContent, CardHeader, CardTitle } from "@tcgscan/ui";
import type { CardOut } from "@tcgscan/sdk-ts";
import { createAlert, deleteAlert, getAlerts, searchCards } from "@tcgscan/sdk-ts";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

export function AlertsClient() {
  const [alerts, setAlerts] = useState<Awaited<ReturnType<typeof getAlerts>>>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<CardOut[]>([]);
  const [selected, setSelected] = useState<CardOut | null>(null);
  const [direction, setDirection] = useState<"below" | "above">("below");
  const [threshold, setThreshold] = useState("250");
  const [formError, setFormError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setAlerts(await getAlerts());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (query.length < 2) {
      setResults([]);
      return;
    }
    const t = setTimeout(() => {
      void searchCards(query, { limit: 6 }).then(setResults).catch(() => setResults([]));
    }, 250);
    return () => clearTimeout(t);
  }, [query]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!selected) {
      setFormError("Pick a card from search results");
      return;
    }
    const amount = parseFloat(threshold);
    if (Number.isNaN(amount) || amount <= 0) {
      setFormError("Enter a valid price threshold");
      return;
    }
    setCreating(true);
    setFormError(null);
    try {
      await createAlert({
        card_id: selected.id,
        direction,
        threshold_usd: amount,
      });
      setSelected(null);
      setQuery("");
      setResults([]);
      await load();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to create alert";
      setFormError(
        msg.includes("403") || msg.includes("Pro")
          ? "Price alerts require Pro — see /account"
          : msg,
      );
    } finally {
      setCreating(false);
    }
  }

  if (loading) return <p className="text-sm text-zinc-500">Loading alerts…</p>;

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Create alert</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={(e) => void handleCreate(e)} className="space-y-4">
            <div>
              <label className="text-sm text-zinc-600">Search card</label>
              <input
                type="search"
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setSelected(null);
                }}
                placeholder="Charizard, Pikachu…"
                className="mt-1 w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm"
              />
              {results.length > 0 && !selected && (
                <ul className="mt-2 divide-y rounded-lg border">
                  {results.map((c) => (
                    <li key={c.id}>
                      <button
                        type="button"
                        className="w-full px-3 py-2 text-left text-sm hover:bg-zinc-50"
                        onClick={() => {
                          setSelected(c);
                          setQuery(c.name);
                          setResults([]);
                        }}
                      >
                        {c.name} · {c.set_name ?? c.set_code}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
              {selected && (
                <p className="mt-2 text-sm text-green-700">
                  Selected: <strong>{selected.name}</strong>
                </p>
              )}
            </div>
            <div className="flex flex-wrap gap-4">
              <div>
                <label className="text-sm text-zinc-600">Direction</label>
                <select
                  value={direction}
                  onChange={(e) => setDirection(e.target.value as "below" | "above")}
                  className="mt-1 block rounded-lg border border-zinc-300 px-3 py-2 text-sm"
                >
                  <option value="below">Drops below</option>
                  <option value="above">Rises above</option>
                </select>
              </div>
              <div>
                <label className="text-sm text-zinc-600">Threshold (USD)</label>
                <input
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={threshold}
                  onChange={(e) => setThreshold(e.target.value)}
                  className="mt-1 block w-32 rounded-lg border border-zinc-300 px-3 py-2 text-sm"
                />
              </div>
            </div>
            {formError && <p className="text-sm text-red-600">{formError}</p>}
            <Button type="submit" disabled={creating}>
              {creating ? "Creating…" : "Create alert"}
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Your alerts</CardTitle>
        </CardHeader>
        <CardContent>
          {alerts.length === 0 ? (
            <p className="text-sm text-zinc-600">
              No alerts yet. Create one above or from a{" "}
              <Link href="/search" className="text-blue-600 underline">
                card detail
              </Link>{" "}
              page.
            </p>
          ) : (
            <ul className="divide-y">
              {alerts.map((a) => (
                <li key={a.id} className="flex items-center justify-between py-3">
                  <div>
                    <Link href={`/card/${a.card.slug}`} className="font-medium hover:underline">
                      {a.card.name}
                    </Link>
                    <p className="text-xs text-zinc-500">
                      Alert when price goes {a.direction} ${a.threshold_usd}
                      {a.grade_filter ? ` (${a.grade_filter})` : ""}
                    </p>
                  </div>
                  <Button size="sm" variant="outline" onClick={() => void deleteAlert(a.id).then(load)}>
                    Delete
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
