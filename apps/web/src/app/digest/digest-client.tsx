"use client";

import { Button, Card, CardContent, CardHeader, CardTitle } from "@tcgscan/ui";
import { getDigestPreview } from "@tcgscan/sdk-ts";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

export function DigestClient() {
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

  if (loading) return <p className="text-sm text-zinc-500">Generating your daily brief…</p>;

  return (
    <div className="space-y-6">
      {error && (
        <Card className="border-amber-200 bg-amber-50">
          <CardContent className="pt-6 text-sm text-amber-900">
            {error}{" "}
            <Link href="/account" className="font-medium underline">
              View plans
            </Link>
          </CardContent>
        </Card>
      )}

      {digest && (
        <Card>
          <CardHeader>
            <CardTitle>{digest.subject}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm text-zinc-700">
            <p className="whitespace-pre-wrap leading-relaxed">{digest.body}</p>
            <p className="text-zinc-500">
              Tracking {digest.portfolio_count} card{digest.portfolio_count === 1 ? "" : "s"} in
              your portfolio.
            </p>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => void load()}>
                Refresh
              </Button>
              <Button asChild variant="outline" size="sm">
                <Link href="/portfolio">View portfolio</Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
