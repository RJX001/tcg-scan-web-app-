"use client";

import { Button, Card, CardContent, CardHeader, CardTitle } from "@tcgscan/ui";
import { getPortfolio, getPortfolioSummary, removeFromPortfolio } from "@tcgscan/sdk-ts";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

export function PortfolioClient() {
  const [items, setItems] = useState<Awaited<ReturnType<typeof getPortfolio>>>([]);
  const [summary, setSummary] = useState<Awaited<ReturnType<typeof getPortfolioSummary>> | null>(
    null,
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setItems(await getPortfolio());
      setSummary(await getPortfolioSummary());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load portfolio");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function remove(id: string) {
    await removeFromPortfolio(id);
    await load();
  }

  if (loading) return <p className="text-sm text-zinc-500">Loading portfolio…</p>;
  if (error) return <p className="text-sm text-red-600">{error}</p>;

  return (
    <div className="space-y-6">
      {summary && summary.item_count > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Collection value</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-zinc-500">Cards</p>
              <p className="text-lg font-semibold">{summary.item_count}</p>
            </div>
            <div>
              <p className="text-zinc-500">Est. value (30d median)</p>
              <p className="text-lg font-semibold">
                {summary.estimated_value_usd != null
                  ? `$${summary.estimated_value_usd.toFixed(2)}`
                  : "—"}
              </p>
            </div>
          </CardContent>
        </Card>
      )}
    <Card>
      <CardHeader>
        <CardTitle>Your collection</CardTitle>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <p className="text-sm text-zinc-600">
            No cards yet.{" "}
            <Link href="/search" className="text-blue-600 underline">
              Search
            </Link>{" "}
            or scan a card and tap Add to portfolio.
          </p>
        ) : (
          <ul className="divide-y">
            {items.map((item) => (
              <li key={item.id} className="flex items-center justify-between py-3">
                <div>
                  <Link href={`/card/${item.card.slug}`} className="font-medium hover:underline">
                    {item.card.name}
                  </Link>
                  <p className="text-xs text-zinc-500">
                    Qty {item.quantity}
                    {item.cost_basis_usd != null && ` · Cost $${item.cost_basis_usd}`}
                  </p>
                </div>
                <Button size="sm" variant="outline" onClick={() => void remove(item.id)}>
                  Remove
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
