"use client";

import { ConditionPanel } from "@/components/condition-panel";
import { Button, Card, CardContent, CardHeader, CardTitle } from "@tcgscan/ui";
import type { ScanResult } from "@tcgscan/sdk-ts";
import { scanCard } from "@tcgscan/sdk-ts";
import Link from "next/link";
import { useCallback, useRef, useState } from "react";

function matchSlug(match: { game?: string | null; set_code?: string | null; number?: string | null }) {
  if (!match.game || !match.set_code) return null;
  const num = (match.number ?? "0").replace("/", "-");
  return `${match.game}-${match.set_code}-${num}`.toLowerCase();
}

export function ScanForm() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ScanResult | null>(null);

  const onFile = useCallback(async (file: File) => {
    setError(null);
    setResult(null);
    setPreview(URL.createObjectURL(file));
    setLoading(true);
    try {
      const out = await scanCard(file, { game: "pokemon", topK: 5 });
      setResult(out);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Scan failed");
    } finally {
      setLoading(false);
    }
  }, []);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-3">
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          capture="environment"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) void onFile(f);
          }}
        />
        <Button onClick={() => inputRef.current?.click()} disabled={loading}>
          {loading ? "Scanning…" : "Upload or capture photo"}
        </Button>
        <p className="text-xs text-zinc-500">
          Run <code className="rounded bg-zinc-100 px-1">pnpm db:seed</code> for demo comps, or ingest
          the catalog for live matching.
        </p>
      </div>

      {preview && (
        // eslint-disable-next-line @next/next/no-img-element -- user upload preview
        <img src={preview} alt="Upload preview" className="max-h-64 rounded-lg border object-contain" />
      )}

      {error && <p className="text-sm text-red-600">{error}</p>}

      {result?.condition.overall != null && (
        <ConditionPanel condition={result.condition} />
      )}

      {result && (
        <Card>
          <CardHeader>
            <CardTitle>Matches</CardTitle>
          </CardHeader>
          <CardContent>
            {result.matches.length === 0 ? (
              <p className="text-sm text-zinc-600">
                No matches — seed demo data or run catalog embed for Qdrant.
              </p>
            ) : (
              <ul className="flex flex-col gap-2">
                {result.matches.map((m) => (
                    <li
                      key={m.card_id}
                      className="flex items-center justify-between rounded-lg border px-3 py-2"
                    >
                      <div>
                        <p className="font-medium">{m.name ?? "Unknown"}</p>
                        <p className="text-xs text-zinc-500">
                          {(m.score * 100).toFixed(0)}% confidence
                        </p>
                      </div>
                      {(m.slug ?? matchSlug(m)) && (
                        <Button asChild size="sm" variant="outline">
                          <Link href={`/card/${m.slug ?? matchSlug(m)}`}>View</Link>
                        </Button>
                      )}
                    </li>
                  ))}
              </ul>
            )}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Demo card</CardTitle>
        </CardHeader>
        <CardContent>
          <Button asChild variant="outline">
            <Link href="/card/pokemon-base1-4-102">Charizard — Base Set 4/102</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
