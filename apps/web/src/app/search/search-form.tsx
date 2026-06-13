"use client";

import { Button } from "@tcgscan/ui";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useRef, useState } from "react";
import type { ScanMatch } from "@tcgscan/sdk-ts";
import { scanCard, searchCards } from "@tcgscan/sdk-ts";

const GAMES = [
  { value: "", label: "All games" },
  { value: "pokemon", label: "Pokemon" },
  { value: "mtg", label: "Magic" },
  { value: "yugioh", label: "Yu-Gi-Oh!" },
  { value: "lorcana", label: "Lorcana" },
  { value: "one_piece", label: "One Piece" },
];

function matchSlug(match: ScanMatch) {
  if (!match.game || !match.set_code) return match.slug ?? null;
  const num = (match.number ?? "0").replace("/", "-");
  return match.slug ?? `${match.game}-${match.set_code}-${num}`.toLowerCase();
}

export function SearchForm() {
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);
  const [mode, setMode] = useState<"text" | "image">("text");
  const [q, setQ] = useState("");
  const [game, setGame] = useState("");
  const [results, setResults] = useState<Awaited<ReturnType<typeof searchCards>>>([]);
  const [imageMatches, setImageMatches] = useState<ScanMatch[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSearch = useCallback(async () => {
    if (!q.trim()) return;
    setLoading(true);
    setError(null);
    setImageMatches([]);
    try {
      const out = await searchCards(q, { game: game || undefined, limit: 24 });
      setResults(out);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search failed");
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, [q, game]);

  const onImageSearch = useCallback(
    async (file: File) => {
      setLoading(true);
      setError(null);
      setResults([]);
      try {
        const out = await scanCard(file, { game: game || "pokemon", topK: 8 });
        setImageMatches(out.matches);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Image search failed");
        setImageMatches([]);
      } finally {
        setLoading(false);
      }
    },
    [game],
  );

  return (
    <div className="flex flex-col gap-4">
      <div className="flex gap-2">
        <Button
          type="button"
          variant={mode === "text" ? "default" : "outline"}
          size="sm"
          onClick={() => setMode("text")}
        >
          Text search
        </Button>
        <Button
          type="button"
          variant={mode === "image" ? "default" : "outline"}
          size="sm"
          onClick={() => setMode("image")}
        >
          Image search
        </Button>
      </div>

      <select
        value={game}
        onChange={(e) => setGame(e.target.value)}
        className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm sm:w-48"
      >
        {GAMES.map((g) => (
          <option key={g.value} value={g.value}>
            {g.label}
          </option>
        ))}
      </select>

      {mode === "text" ? (
        <div className="flex flex-col gap-2 sm:flex-row">
          <input
            type="search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && void onSearch()}
            placeholder="Search by name, set, or number…"
            className="flex-1 rounded-lg border border-zinc-300 px-3 py-2 text-sm"
          />
          <Button onClick={() => void onSearch()} disabled={loading || !q.trim()}>
            {loading ? "Searching…" : "Search"}
          </Button>
        </div>
      ) : (
        <div className="rounded-lg border border-dashed border-zinc-300 p-6 text-center">
          <p className="text-sm text-zinc-600">Upload a card photo to find catalog matches</p>
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) void onImageSearch(f);
            }}
          />
          <Button className="mt-3" onClick={() => fileRef.current?.click()} disabled={loading}>
            {loading ? "Scanning…" : "Upload image"}
          </Button>
        </div>
      )}

      {error && <p className="text-sm text-red-600">{error}</p>}

      {results.length > 0 && (
        <ul className="divide-y rounded-lg border">
          {results.map((card) => (
            <li key={card.id}>
              <Link
                href={`/card/${card.slug}`}
                className="flex items-center justify-between px-4 py-3 hover:bg-zinc-50"
              >
                <div>
                  <p className="font-medium">{card.name}</p>
                  <p className="text-xs text-zinc-500">
                    {card.game} · {card.set_name ?? card.set_code} · {card.number}
                  </p>
                </div>
                <span className="text-sm text-blue-600">View →</span>
              </Link>
            </li>
          ))}
        </ul>
      )}

      {imageMatches.length > 0 && (
        <ul className="divide-y rounded-lg border">
          {imageMatches.map((m) => {
            const slug = matchSlug(m);
            return (
              <li key={m.card_id}>
                {slug ? (
                  <Link
                    href={`/card/${slug}`}
                    className="flex items-center justify-between px-4 py-3 hover:bg-zinc-50"
                  >
                    <div>
                      <p className="font-medium">{m.name ?? "Unknown"}</p>
                      <p className="text-xs text-zinc-500">{(m.score * 100).toFixed(0)}% match</p>
                    </div>
                    <span className="text-sm text-blue-600">View →</span>
                  </Link>
                ) : (
                  <div className="px-4 py-3 text-sm">{m.name ?? m.card_id}</div>
                )}
              </li>
            );
          })}
        </ul>
      )}

      <p className="text-xs text-zinc-500">
        Tip: use{" "}
        <button type="button" className="text-blue-600 underline" onClick={() => router.push("/scan")}>
          Scan
        </button>{" "}
        for condition grading and ROI on a photo.
      </p>
    </div>
  );
}
