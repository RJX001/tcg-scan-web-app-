"use client";

import { Button } from "@tcgscan/ui";
import { addToPortfolio, createAlert } from "@tcgscan/sdk-ts";
import { useState } from "react";

type Props = {
  cardId: string;
  cardName: string;
};

export function CardActions({ cardId, cardName }: Props) {
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

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

  async function handleAlert() {
    setLoading(true);
    setStatus(null);
    try {
      await createAlert({ card_id: cardId, direction: "below", threshold_usd: 1 });
      setStatus("Price alert created (below $1 — edit in Alerts)");
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Failed to create alert");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-wrap gap-2">
      <Button onClick={() => void handlePortfolio()} disabled={loading} variant="default">
        Add to portfolio
      </Button>
      <Button onClick={() => void handleAlert()} disabled={loading} variant="outline">
        Set price alert
      </Button>
      {status && <p className="w-full text-sm text-zinc-600">{status}</p>}
    </div>
  );
}
