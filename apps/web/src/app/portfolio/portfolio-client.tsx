"use client";

import { Button, Card, CardContent, CardHeader, CardTitle } from "@tcgscan/ui";
import { getPortfolio, removeFromPortfolio } from "@tcgscan/sdk-ts";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

export function PortfolioClient() {
  const [items, setItems] = useState<Awaited<ReturnType<typeof getPortfolio>>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setItems(await getPortfolio());
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
  );
}
