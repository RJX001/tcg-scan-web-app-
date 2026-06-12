"use client";

import { Button } from "@tcgscan/ui";
import { addToPortfolio, addToWatchlist, createAlert } from "@tcgscan/sdk-ts";
import { useState } from "react";

type Props = {
  cardId: string;
  cardName: string;
  medianUsd?: number | null;
};

export function CardActions({ cardId, cardName, medianUsd }: Props) {
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [showAlertForm, setShowAlertForm] = useState(false);
  const [direction, setDirection] = useState<"below" | "above">("below");
  const [threshold, setThreshold] = useState(
    medianUsd != null ? String(Math.round(medianUsd * 0.9)) : "250",
  );

  async function handlePortfolio() {
    setLoading(true);
    setStatus(null);
    try {
      await addToPortfolio({ card_id: cardId, quantity: 1 });
      setStatus(`Added ${cardName} to portfolio`);
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Failed to add");
    } finally {
      setLoading(false);
    }
  }

  async function handleWatch() {
    setLoading(true);
    setStatus(null);
    try {
      await addToWatchlist(cardId);
      setStatus(`Watching ${cardName} — see /watchlist`);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to watch";
      setStatus(
        msg.includes("403") || msg.includes("Pro")
          ? "Watchlist requires Pro — see /account"
          : msg,
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleAlert() {
    setLoading(true);
    setStatus(null);
    const amount = parseFloat(threshold);
    if (Number.isNaN(amount) || amount <= 0) {
      setStatus("Enter a valid threshold");
      setLoading(false);
      return;
    }
    try {
      await createAlert({ card_id: cardId, direction, threshold_usd: amount });
      setStatus(`Alert set: notify when price goes ${direction} $${amount.toFixed(2)}`);
      setShowAlertForm(false);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to create alert";
      setStatus(
        msg.includes("403") || msg.includes("Pro")
          ? "Price alerts require Pro — see /account"
          : msg,
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap gap-2">
        <Button onClick={() => void handlePortfolio()} disabled={loading} variant="default">
          Add to portfolio
        </Button>
        <Button onClick={() => void handleWatch()} disabled={loading} variant="outline">
          Watch
        </Button>
        <Button
          onClick={() => setShowAlertForm((v) => !v)}
          disabled={loading}
          variant="outline"
        >
          Set price alert
        </Button>
      </div>
      {showAlertForm && (
        <div className="flex flex-wrap items-end gap-3 rounded-lg border border-zinc-200 bg-zinc-50 p-3">
          <div>
            <label className="text-xs text-zinc-500">Direction</label>
            <select
              value={direction}
              onChange={(e) => setDirection(e.target.value as "below" | "above")}
              className="mt-1 block rounded border border-zinc-300 px-2 py-1 text-sm"
            >
              <option value="below">Drops below</option>
              <option value="above">Rises above</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-zinc-500">Threshold (USD)</label>
            <input
              type="number"
              min="0.01"
              step="0.01"
              value={threshold}
              onChange={(e) => setThreshold(e.target.value)}
              className="mt-1 block w-28 rounded border border-zinc-300 px-2 py-1 text-sm"
            />
          </div>
          <Button size="sm" onClick={() => void handleAlert()} disabled={loading}>
            Save alert
          </Button>
        </div>
      )}
      {status && <p className="text-sm text-zinc-600">{status}</p>}
    </div>
  );
}
