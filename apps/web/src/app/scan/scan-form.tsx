"use client";

import { ConditionPanel } from "@/components/condition-panel";
import { Button, Card, CardContent, CardHeader, CardTitle } from "@tcgscan/ui";
import type { ScanMatch, ScanResult } from "@tcgscan/sdk-ts";
import { scanCard } from "@tcgscan/sdk-ts";
import Link from "next/link";
import { useCallback, useRef, useState } from "react";

const GAMES = [
  { value: "pokemon", label: "Pokemon" },
  { value: "mtg", label: "Magic" },
  { value: "yugioh", label: "Yu-Gi-Oh!" },
  { value: "lorcana", label: "Lorcana" },
  { value: "one_piece", label: "One Piece" },
];

function matchSlug(match: { game?: string | null; set_code?: string | null; number?: string | null }) {
  if (!match.game || !match.set_code) return null;
  const num = (match.number ?? "0").replace("/", "-");
  return `${match.game}-${match.set_code}-${num}`.toLowerCase();
}

type Stage = "idle" | "detect" | "match" | "grade" | "done";

export function ScanForm() {
  const inputRef = useRef<HTMLInputElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [stage, setStage] = useState<Stage>("idle");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ScanResult | null>(null);
  const [game, setGame] = useState("pokemon");
  const [cameraOn, setCameraOn] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [selectedMatch, setSelectedMatch] = useState<ScanMatch | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const streamRef = useRef<MediaStream | null>(null);

  const runScan = useCallback(
    async (file: File | Blob) => {
      setError(null);
      setResult(null);
      setSelectedMatch(null);
      setConfirmed(false);
      setPreview(URL.createObjectURL(file));
      setLoading(true);
      setStage("detect");
      try {
        setStage("match");
        const out = await scanCard(file, { game, topK: 5 });
        setStage("grade");
        setResult(out);
        setStage("done");
        const top = out.matches[0];
        if (top) setSelectedMatch(top);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Scan failed");
        setStage("idle");
      } finally {
        setLoading(false);
      }
    },
    [game],
  );

  const onFile = useCallback(
    (file: File) => {
      void runScan(file);
    },
    [runScan],
  );

  const startCamera = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment" },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setCameraOn(true);
    } catch {
      setError("Camera unavailable — use upload instead");
    }
  }, []);

  const stopCamera = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    setCameraOn(false);
  }, []);

  const captureFromCamera = useCallback(async () => {
    const video = videoRef.current;
    if (!video) return;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(video, 0, 0);
    canvas.toBlob((blob) => {
      if (blob) void runScan(blob);
      stopCamera();
    }, "image/jpeg", 0.92);
  }, [runScan, stopCamera]);

  const stageLabel: Record<Stage, string> = {
    idle: "",
    detect: "Detecting card…",
    match: "Searching catalog…",
    grade: "Grading condition…",
    done: "Done",
  };

  const needsConfirm = selectedMatch != null && selectedMatch.score < 0.75 && !confirmed;
  const selectedSlug = selectedMatch ? (selectedMatch.slug ?? matchSlug(selectedMatch)) : null;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center gap-2">
        <label className="text-sm text-zinc-600">Game:</label>
        <select
          value={game}
          onChange={(e) => setGame(e.target.value)}
          className="rounded-lg border border-zinc-300 px-2 py-1 text-sm"
        >
          {GAMES.map((g) => (
            <option key={g.value} value={g.value}>
              {g.label}
            </option>
          ))}
        </select>
      </div>

      <div
        className={`rounded-xl border-2 border-dashed p-8 text-center transition-colors ${
          dragOver ? "border-blue-400 bg-blue-50" : "border-zinc-200"
        }`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          const f = e.dataTransfer.files[0];
          if (f?.type.startsWith("image/")) onFile(f);
        }}
      >
        <p className="text-sm text-zinc-600">Drag & drop a card photo, or use the buttons below</p>
        <div className="mt-4 flex flex-wrap justify-center gap-2">
          <input
            ref={inputRef}
            type="file"
            accept="image/*"
            capture="environment"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) onFile(f);
            }}
          />
          <Button onClick={() => inputRef.current?.click()} disabled={loading}>
            Upload photo
          </Button>
          {!cameraOn ? (
            <Button variant="outline" onClick={() => void startCamera()} disabled={loading}>
              Open camera
            </Button>
          ) : (
            <>
              <Button onClick={() => void captureFromCamera()} disabled={loading}>
                Capture
              </Button>
              <Button variant="outline" onClick={stopCamera}>
                Close camera
              </Button>
            </>
          )}
        </div>
      </div>

      {cameraOn && (
        <video ref={videoRef} className="max-h-64 w-full rounded-lg border object-contain" muted playsInline />
      )}

      {loading && stage !== "idle" && (
        <p className="text-sm font-medium text-blue-600">{stageLabel[stage]}</p>
      )}

      {preview && (
        <div className="relative inline-block">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={preview} alt="Upload preview" className="max-h-64 rounded-lg border object-contain" />
          {result?.bbox && (
            <div
              className="pointer-events-none absolute border-2 border-green-500"
              style={{
                left: `${result.bbox.x * 100}%`,
                top: `${result.bbox.y * 100}%`,
                width: `${result.bbox.w * 100}%`,
                height: `${result.bbox.h * 100}%`,
              }}
            />
          )}
        </div>
      )}

      {error && <p className="text-sm text-red-600">{error}</p>}

      {result?.condition.overall != null && <ConditionPanel condition={result.condition} />}

      {result && result.matches.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>
              {needsConfirm ? "Confirm your match" : confirmed ? "Match confirmed" : "Top matches"}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {needsConfirm && (
              <p className="mb-3 text-sm text-amber-800">
                Confidence is below 75% — tap the correct card below, then confirm.
              </p>
            )}
            <ul className="flex flex-col gap-2">
              {result.matches.map((m) => {
                const isSelected = selectedMatch?.card_id === m.card_id;
                const slug = m.slug ?? matchSlug(m);
                return (
                  <li
                    key={m.card_id}
                    className={`flex items-center justify-between rounded-lg border px-3 py-2 transition-colors ${
                      isSelected ? "border-blue-500 bg-blue-50" : "border-zinc-200"
                    }`}
                  >
                    <button
                      type="button"
                      className="flex flex-1 flex-col items-start text-left"
                      onClick={() => {
                        setSelectedMatch(m);
                        setConfirmed(false);
                      }}
                    >
                      <p className="font-medium">{m.name ?? "Unknown"}</p>
                      <p className="text-xs text-zinc-500">
                        {(m.score * 100).toFixed(0)}% match · OCR ×{(m.ocr_boost ?? 1).toFixed(2)}
                      </p>
                    </button>
                    <div className="flex gap-2">
                      {isSelected && !confirmed && (
                        <Button size="sm" onClick={() => setConfirmed(true)}>
                          Confirm
                        </Button>
                      )}
                      {slug && (
                        <Button asChild size="sm" variant="outline">
                          <Link href={`/card/${slug}`}>View</Link>
                        </Button>
                      )}
                    </div>
                  </li>
                );
              })}
            </ul>
            {confirmed && selectedSlug && (
              <div className="mt-4 rounded-lg bg-green-50 p-3 text-sm text-green-900">
                Confirmed: <strong>{selectedMatch?.name}</strong>.{" "}
                <Link href={`/card/${selectedSlug}`} className="font-medium underline">
                  Open card detail →
                </Link>
              </div>
            )}
            {result.stages_ms && (
              <p className="mt-3 text-xs text-zinc-400">
                {Object.entries(result.stages_ms)
                  .map(([k, v]) => `${k}: ${v.toFixed(0)}ms`)
                  .join(" · ")}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {result && result.matches.length === 0 && (
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-zinc-600">
              No matches — run{" "}
              <code className="rounded bg-zinc-100 px-1">pnpm db:seed</code> and{" "}
              <code className="rounded bg-zinc-100 px-1">pnpm embed:catalog</code>.
            </p>
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
