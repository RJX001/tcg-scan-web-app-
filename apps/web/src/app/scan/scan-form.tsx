"use client";

import { ConditionPanel } from "@/components/condition-panel";
import { MarketplacePrices } from "@/components/marketplace-prices";
import { DEMO_CARDS, SCAN_GAMES } from "@/lib/games";
import type { ScanMatch, ScanResult } from "@tcgscan/sdk-ts";
import { scanCard } from "@tcgscan/sdk-ts";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

function matchSlug(match: { game?: string | null; set_code?: string | null; number?: string | null }) {
  if (!match.game || !match.set_code) return null;
  const num = (match.number ?? "0").replace("/", "-");
  return `${match.game}-${match.set_code}-${num}`.toLowerCase();
}

type Stage = "idle" | "detect" | "match" | "grade" | "done";

const SCAN_STEPS = [
  { n: 1, t: "Frame the card", d: "Camera or photo upload. Works for raw and slabbed cards." },
  { n: 2, t: "We match it", d: "AI vision identifies the card, set, number and grade." },
  { n: 3, t: "Sold data + listings appear", d: "Real prices from every major marketplace." },
  { n: 4, t: "Verdict at the bottom", d: "Buy, hold or sell — with the reasons, on the card page." },
] as const;

export function ScanForm() {
  const router = useRouter();
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
  const [searchQ, setSearchQ] = useState("");
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
      setCameraOn(true);
    } catch {
      setError("Camera unavailable — use upload instead");
    }
  }, []);

  useEffect(() => {
    if (!cameraOn || !streamRef.current || !videoRef.current) return;
    const video = videoRef.current;
    video.srcObject = streamRef.current;
    void video.play();
  }, [cameraOn]);

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
    canvas.toBlob(
      (blob) => {
        if (blob) void runScan(blob);
        stopCamera();
      },
      "image/jpeg",
      0.92,
    );
  }, [runScan, stopCamera]);

  const stageLabel: Record<Stage, string> = {
    idle: "Hold steady · identifying card",
    detect: "Detecting card…",
    match: "Searching catalog…",
    grade: "Grading condition…",
    done: "Match ready",
  };

  const needsConfirm = selectedMatch != null && selectedMatch.score < 0.75 && !confirmed;
  const selectedSlug = selectedMatch ? (selectedMatch.slug ?? matchSlug(selectedMatch)) : null;
  const statusText = loading ? stageLabel[stage] : cameraOn ? "Camera live · capture when ready" : stageLabel.idle;

  return (
    <div style={{ paddingBottom: 48 }}>
      <style>{`
        @keyframes cc-scan { 0%, 100% { top: 14%; } 50% { top: 82%; } }
        @keyframes cc-pulse { 0%, 100% { opacity: .5; } 50% { opacity: 1; } }
        @keyframes cc-fade { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }
        .cc-scan-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 40px; align-items: center; padding: 48px 0; animation: cc-fade .4s ease; }
        @media (max-width: 860px) { .cc-scan-grid { grid-template-columns: 1fr; gap: 28px; padding: 32px 0; } }
        .cc-scan-btn { font-family: var(--font-body); font-size: 13.5px; font-weight: 700; padding: 11px 18px; border-radius: 11px; border: none; cursor: pointer; }
        .cc-scan-btn:disabled { opacity: .55; cursor: not-allowed; }
        .cc-scan-btn-primary { background: var(--accent); color: var(--accent-ink); }
        .cc-scan-btn-ghost { background: transparent; border: 1px solid var(--border); color: var(--text); }
        .cc-chip { font-size: 12.5px; font-weight: 600; padding: 7px 13px; border-radius: 99px; border: 1px solid var(--border); background: var(--surface); color: var(--text2); white-space: nowrap; cursor: pointer; }
        .cc-chip[data-active="true"] { background: var(--accent); color: var(--accent-ink); border-color: var(--accent); }
        .cc-match { border: 1px solid var(--border); border-radius: 12px; padding: 12px 14px; background: var(--surface); display: flex; align-items: center; justify-content: space-between; gap: 12px; }
        .cc-match[data-selected="true"] { border-color: var(--accent); background: var(--accent-soft); }
      `}</style>

      <div className="cc-scan-grid">
        {/* Viewfinder */}
        <div
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
          style={{
            aspectRatio: "4 / 3",
            borderRadius: 22,
            position: "relative",
            overflow: "hidden",
            background: "var(--panel)",
            border: dragOver ? "1px solid var(--panel-gold)" : "1px solid var(--panel-border)",
            boxShadow: "0 30px 70px -24px rgba(20,18,10,0.22)",
            color: "var(--panel-text)",
          }}
        >
          {/* Reticle corners */}
          <div style={{ position: "absolute", top: 36, left: 36, width: 30, height: 30, border: "3px solid var(--panel-gold)", borderRight: 0, borderBottom: 0, borderRadius: "8px 0 0 0", zIndex: 3 }} />
          <div style={{ position: "absolute", top: 36, right: 36, width: 30, height: 30, border: "3px solid var(--panel-gold)", borderLeft: 0, borderBottom: 0, borderRadius: "0 8px 0 0", zIndex: 3 }} />
          <div style={{ position: "absolute", bottom: 36, left: 36, width: 30, height: 30, border: "3px solid var(--panel-gold)", borderRight: 0, borderTop: 0, borderRadius: "0 0 0 8px", zIndex: 3 }} />
          <div style={{ position: "absolute", bottom: 36, right: 36, width: 30, height: 30, border: "3px solid var(--panel-gold)", borderLeft: 0, borderTop: 0, borderRadius: "0 0 8px 0", zIndex: 3 }} />

          {/* Ghost card / preview / camera */}
          <div
            style={{
              position: "absolute",
              top: "50%",
              left: "50%",
              transform: "translate(-50%, -50%)",
              width: 150,
              aspectRatio: "5 / 7",
              borderRadius: 12,
              border: "1px solid var(--panel-gold)",
              boxShadow: "0 0 40px rgba(0,0,0,0.3)",
              overflow: "hidden",
              zIndex: 1,
              background: preview || cameraOn
                ? "#111"
                : "repeating-linear-gradient(135deg, var(--panel2), var(--panel2) 8px, var(--panel) 8px, var(--panel) 16px)",
            }}
          >
            {cameraOn && (
              <video
                ref={videoRef}
                muted
                playsInline
                style={{ width: "100%", height: "100%", objectFit: "cover" }}
              />
            )}
            {preview && !cameraOn && (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={preview} alt="Upload preview" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
            )}
            {result?.bbox && preview && !cameraOn && (
              <div
                style={{
                  pointerEvents: "none",
                  position: "absolute",
                  border: "2px solid #34D499",
                  left: `${result.bbox.x * 100}%`,
                  top: `${result.bbox.y * 100}%`,
                  width: `${result.bbox.w * 100}%`,
                  height: `${result.bbox.h * 100}%`,
                }}
              />
            )}
          </div>

          {/* Scanning line */}
          <div
            style={{
              position: "absolute",
              left: 36,
              right: 36,
              height: 2,
              background: "linear-gradient(90deg, transparent, var(--panel-gold), transparent)",
              animation: "cc-scan 2.6s ease-in-out infinite",
              zIndex: 2,
            }}
          />

          <div
            style={{
              position: "absolute",
              bottom: 16,
              left: 0,
              right: 0,
              textAlign: "center",
              fontSize: 11,
              letterSpacing: "0.2em",
              textTransform: "uppercase",
              color: "var(--panel-gold)",
              fontWeight: 700,
              animation: "cc-pulse 1.6s ease-in-out infinite",
              zIndex: 3,
            }}
          >
            {statusText}
          </div>
        </div>

        {/* Copy column */}
        <div>
          <div
            style={{
              fontSize: 11,
              fontWeight: 700,
              letterSpacing: "0.14em",
              textTransform: "uppercase",
              color: "var(--eyebrow)",
            }}
          >
            Scan
          </div>
          <h1
            style={{
              fontFamily: "var(--font-display)",
              fontSize: "clamp(28px, 4vw, 36px)",
              fontWeight: 800,
              letterSpacing: "-0.025em",
              lineHeight: 1.05,
              marginTop: 10,
            }}
          >
            Point. Identify. Know.
          </h1>
          <p style={{ color: "var(--text2)", fontSize: 15.5, marginTop: 14, maxWidth: 440, lineHeight: 1.6 }}>
            CardChart recognises the card and its grade, then instantly pulls sold prices and active
            listings from every marketplace — and reads you a verdict.
          </p>

          <div style={{ marginTop: 22, display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center" }}>
            <span style={{ fontSize: 12, fontWeight: 700, color: "var(--text3)", letterSpacing: "0.06em", textTransform: "uppercase" }}>
              Game
            </span>
            {SCAN_GAMES.map((g) => (
              <button
                key={g.value}
                type="button"
                className="cc-chip"
                data-active={game === g.value}
                onClick={() => setGame(g.value)}
              >
                {g.label}
              </button>
            ))}
          </div>

          <div style={{ marginTop: 18, display: "flex", flexWrap: "wrap", gap: 10 }}>
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
            <button
              type="button"
              className="cc-scan-btn cc-scan-btn-primary"
              onClick={() => inputRef.current?.click()}
              disabled={loading}
            >
              Upload photo
            </button>
            {!cameraOn ? (
              <button
                type="button"
                className="cc-scan-btn cc-scan-btn-ghost"
                onClick={() => void startCamera()}
                disabled={loading}
              >
                Open camera
              </button>
            ) : (
              <>
                <button
                  type="button"
                  className="cc-scan-btn cc-scan-btn-primary"
                  onClick={() => void captureFromCamera()}
                  disabled={loading}
                >
                  Capture
                </button>
                <button type="button" className="cc-scan-btn cc-scan-btn-ghost" onClick={stopCamera}>
                  Close camera
                </button>
              </>
            )}
          </div>

          <div style={{ marginTop: 26, display: "grid", gap: 14 }}>
            {SCAN_STEPS.map((s) => (
              <div key={s.n} style={{ display: "flex", gap: 13, alignItems: "flex-start" }}>
                <div
                  style={{
                    width: 28,
                    height: 28,
                    borderRadius: 8,
                    flex: "none",
                    background: "var(--accent-soft)",
                    color: "var(--accent)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: 12.5,
                    fontWeight: 800,
                    fontFamily: "var(--font-num)",
                  }}
                >
                  {s.n}
                </div>
                <div>
                  <div style={{ fontWeight: 700, fontSize: 14.5 }}>{s.t}</div>
                  <div style={{ fontSize: 13, color: "var(--text2)", marginTop: 1 }}>{s.d}</div>
                </div>
              </div>
            ))}
          </div>

          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              marginTop: 26,
              color: "var(--text3)",
              fontSize: 12,
            }}
          >
            <span style={{ flex: 1, height: 1, background: "var(--border)" }} />
            or search instead
            <span style={{ flex: 1, height: 1, background: "var(--border)" }} />
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              const q = searchQ.trim();
              if (q) router.push(`/search?q=${encodeURIComponent(q)}`);
              else router.push("/search");
            }}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: 12,
              padding: "12px 16px",
              marginTop: 16,
              boxShadow: "0 1px 2px rgba(23,24,28,0.05)",
            }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
              <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
              <path d="m20 20-3-3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
            <input
              type="search"
              value={searchQ}
              onChange={(e) => setSearchQ(e.target.value)}
              placeholder='Try "Charizard Base Set"…'
              style={{
                flex: 1,
                border: "none",
                outline: "none",
                background: "transparent",
                fontSize: 14,
                color: "var(--text)",
                fontFamily: "var(--font-body)",
              }}
            />
          </form>
        </div>
      </div>

      {error && (
        <p style={{ color: "#D6444B", fontSize: 14, marginBottom: 16 }}>{error}</p>
      )}

      {result?.condition.overall != null && (
        <div style={{ marginBottom: 20 }}>
          <ConditionPanel condition={result.condition} />
        </div>
      )}

      {result && result.matches.length > 0 && (
        <div
          style={{
            background: "var(--panel)",
            border: "1px solid var(--panel-border)",
            borderRadius: 18,
            padding: 20,
            color: "var(--panel-text)",
            boxShadow: "0 1px 2px rgba(23,24,28,0.05)",
            marginBottom: 24,
          }}
        >
          <div
            style={{
              fontSize: 11,
              fontWeight: 700,
              letterSpacing: "0.14em",
              textTransform: "uppercase",
              color: "var(--panel-gold)",
            }}
          >
            {needsConfirm ? "Confirm your match" : confirmed ? "Match confirmed" : "Top matches"}
          </div>
          {needsConfirm && (
            <p style={{ fontSize: 13.5, color: "var(--panel-text2)", marginTop: 8 }}>
              Confidence is below 75% — tap the correct card below, then confirm.
            </p>
          )}
          <ul style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 14, listStyle: "none", padding: 0 }}>
            {result.matches.map((m) => {
              const isSelected = selectedMatch?.card_id === m.card_id;
              const slug = m.slug ?? matchSlug(m);
              return (
                <li key={m.card_id} className="cc-match" data-selected={isSelected} style={{ background: isSelected ? "rgba(224,185,74,0.12)" : "var(--panel2)", borderColor: isSelected ? "var(--panel-gold)" : "var(--panel-border)", color: "var(--panel-text)" }}>
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedMatch(m);
                      setConfirmed(false);
                    }}
                    style={{
                      flex: 1,
                      textAlign: "left",
                      background: "none",
                      border: "none",
                      color: "inherit",
                      cursor: "pointer",
                      fontFamily: "var(--font-body)",
                    }}
                  >
                    <p style={{ fontWeight: 600, fontSize: 14.5, margin: 0 }}>{m.name ?? "Unknown"}</p>
                    <p style={{ fontSize: 12, color: "var(--panel-text3)", margin: "2px 0 0" }}>
                      {(m.score * 100).toFixed(0)}% match · OCR ×{(m.ocr_boost ?? 1).toFixed(2)}
                    </p>
                  </button>
                  <div style={{ display: "flex", gap: 8 }}>
                    {isSelected && !confirmed && (
                      <button type="button" className="cc-scan-btn cc-scan-btn-primary" style={{ padding: "8px 12px", fontSize: 12 }} onClick={() => setConfirmed(true)}>
                        Confirm
                      </button>
                    )}
                    {slug && (
                      <Link
                        href={`/card/${slug}`}
                        style={{
                          fontSize: 12,
                          fontWeight: 700,
                          padding: "8px 12px",
                          borderRadius: 8,
                          border: "1px solid var(--panel-border)",
                          color: "var(--panel-text)",
                          textDecoration: "none",
                        }}
                      >
                        View
                      </Link>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
          {confirmed && selectedMatch && (
            <div style={{ marginTop: 16 }}>
              <div
                style={{
                  borderRadius: 12,
                  padding: 12,
                  background: "rgba(52,212,153,0.12)",
                  color: "#34D499",
                  fontSize: 13.5,
                }}
              >
                Confirmed: <strong>{selectedMatch.name}</strong>
                {selectedSlug ? (
                  <>
                    .{" "}
                    <Link href={`/card/${selectedSlug}`} style={{ color: "inherit", fontWeight: 700 }}>
                      Open full card detail →
                    </Link>
                  </>
                ) : null}
              </div>
              <div style={{ marginTop: 16 }}>
                <MarketplacePrices cardId={selectedMatch.card_id} />
              </div>
            </div>
          )}
          {result.stages_ms && (
            <p style={{ marginTop: 12, fontSize: 11, color: "var(--panel-text3)", fontFamily: "var(--font-num)" }}>
              {Object.entries(result.stages_ms)
                .map(([k, v]) => `${k}: ${v.toFixed(0)}ms`)
                .join(" · ")}
            </p>
          )}
        </div>
      )}

      {result && result.matches.length === 0 && (
        <div
          style={{
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: 18,
            padding: 20,
            marginBottom: 24,
          }}
        >
          <p style={{ fontSize: 14, color: "var(--text2)", margin: 0 }}>
            No matches — pick the correct game above, then run{" "}
            <code style={{ background: "var(--surface2)", padding: "1px 6px", borderRadius: 6 }}>pnpm db:demo</code>{" "}
            to load TCG catalogs into Qdrant.
          </p>
        </div>
      )}

      <div
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: 18,
          padding: 22,
          boxShadow: "0 1px 2px rgba(23,24,28,0.05)",
        }}
      >
        <div style={{ fontFamily: "var(--font-display)", fontWeight: 700, fontSize: 17 }}>Demo cards</div>
        <div style={{ marginTop: 14, display: "flex", flexDirection: "column", gap: 14 }}>
          {(["pokemon", "mtg", "yugioh", "lorcana", "one_piece"] as const).map((g) => (
            <div key={g}>
              <p
                style={{
                  margin: "0 0 8px",
                  fontSize: 11,
                  fontWeight: 700,
                  letterSpacing: "0.1em",
                  textTransform: "uppercase",
                  color: "var(--text3)",
                }}
              >
                {SCAN_GAMES.find((x) => x.value === g)?.label ?? g}
              </p>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                {DEMO_CARDS.filter((c) => c.game === g).map(({ slug, label }) => (
                  <Link
                    key={slug}
                    href={`/card/${slug}`}
                    style={{
                      fontSize: 12.5,
                      fontWeight: 600,
                      padding: "7px 12px",
                      borderRadius: 99,
                      border: "1px solid var(--border)",
                      background: "var(--surface)",
                      color: "var(--text2)",
                      textDecoration: "none",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {label}
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
