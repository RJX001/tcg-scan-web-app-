"use client";

import { Button } from "@tcgscan/ui";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useState } from "react";
import { searchCards } from "@tcgscan/sdk-ts";

const GAMES = [
  { value: "", label: "All games" },
  { value: "pokemon", label: "Pokemon" },
  { value: "mtg", label: "Magic" },
  { value: "yugioh", label: "Yu-Gi-Oh!" },
  { value: "lorcana", label: "Lorcana" },
  { value: "one_piece", label: "One Piece" },
];

export function SearchForm() {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [game, setGame] = useState("");
  const [results, setResults] = useState<Awaited<ReturnType<typeof searchCards>>>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSearch = useCallback(async () => {
    if (!q.trim()) return;
    setLoading(true);
    setError(null);
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

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-2 sm:flex-row">
        <input
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && void onSearch()}
          placeholder="Search by name, set, or number…"
          className="flex-1 rounded-lg border border-zinc-300 px-3 py-2 text-sm"
        />
        <select
          value={game}
          onChange={(e) => setGame(e.target.value)}
          className="rounded-lg border border-zinc-300 px-3 py-2 text-sm"
        >
          {GAMES.map((g) => (
            <option key={g.value} value={g.value}>
              {g.label}
            </option>
          ))}
        </select>
        <Button onClick={() => void onSearch()} disabled={loading || !q.trim()}>
          {loading ? "Searching…" : "Search"}
        </Button>
      </div>

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

      <p className="text-xs text-zinc-500">
        Tip: use{" "}
        <button type="button" className="text-blue-600 underline" onClick={() => router.push("/scan")}>
          Scan
        </button>{" "}
        for image-based matching.
      </p>
    </div>
  );
}
