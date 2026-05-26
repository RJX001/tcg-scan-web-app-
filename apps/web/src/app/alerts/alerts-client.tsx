"use client";

import { Button, Card, CardContent, CardHeader, CardTitle } from "@tcgscan/ui";
import { deleteAlert, getAlerts } from "@tcgscan/sdk-ts";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

export function AlertsClient() {
  const [alerts, setAlerts] = useState<Awaited<ReturnType<typeof getAlerts>>>([]);
  const [loading, setLoading] = useState(true);

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

  if (loading) return <p className="text-sm text-zinc-500">Loading alerts…</p>;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Price alerts</CardTitle>
      </CardHeader>
      <CardContent>
        {alerts.length === 0 ? (
          <p className="text-sm text-zinc-600">
            No alerts. Set one from a{" "}
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
  );
}
