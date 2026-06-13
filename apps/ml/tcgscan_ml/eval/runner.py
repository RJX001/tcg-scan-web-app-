"""Eval harness — top-1/top-5, condition MAE, latency percentiles."""

from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
import time
from pathlib import Path


def _load_fixture(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _score_live(api_url: str, rows: list[dict[str, str]]) -> dict[str, object]:
    import httpx

    top1 = 0
    top5 = 0
    latencies: list[float] = []
    for row in rows:
        image_path = row.get("image_path", "")
        true_id = row.get("true_card_id", "")
        if not image_path or not Path(image_path).exists():
            continue
        started = time.perf_counter()
        with Path(image_path).open("rb") as fh:
            files = {"image": fh}
            with httpx.Client(timeout=30.0) as client:
                r = client.post(f"{api_url.rstrip('/')}/v1/scan", files=files)
        latencies.append((time.perf_counter() - started) * 1000)
        if r.status_code != 200:
            continue
        matches = r.json().get("matches") or []
        ids = [m.get("card_id") for m in matches[:5]]
        if ids and ids[0] == true_id:
            top1 += 1
        if true_id in ids:
            top5 += 1
    n = len(latencies) or 1
    return {
        "status": "ok",
        "samples": len(latencies),
        "top1_accuracy": top1 / n,
        "top5_accuracy": top5 / n,
        "condition_mae": None,
        "latency_p50_ms": statistics.median(latencies) if latencies else None,
        "latency_p95_ms": sorted(latencies)[int(len(latencies) * 0.95) - 1] if latencies else None,
        "mode": "live_api",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser("tcgscan eval")
    parser.add_argument(
        "--fixture",
        default=str(Path(__file__).resolve().parents[2] / "eval" / "fixtures" / "sample.csv"),
    )
    parser.add_argument(
        "--report",
        default=str(Path(__file__).resolve().parents[2] / "eval" / "reports" / "latest.json"),
    )
    parser.add_argument("--api-url", default=os.getenv("EVAL_API_URL", ""))
    args = parser.parse_args(argv)

    rows = _load_fixture(Path(args.fixture))
    if not rows:
        report: dict[str, object] = {
            "status": "skipped",
            "message": "No fixture rows — add eval/fixtures/sample.csv with image_path,true_card_id",
            "top1_accuracy": None,
            "top5_accuracy": None,
            "condition_mae": None,
            "latency_p50_ms": None,
            "latency_p95_ms": None,
        }
    elif args.api_url:
        report = _score_live(args.api_url, rows)
    else:
        latencies = [120.0 + i * 5 for i in range(len(rows))]
        report = {
            "status": "ok",
            "samples": len(rows),
            "top1_accuracy": 0.0,
            "top5_accuracy": 0.0,
            "condition_mae": 1.5,
            "latency_p50_ms": statistics.median(latencies),
            "latency_p95_ms": sorted(latencies)[int(len(latencies) * 0.95) - 1],
            "note": "Stub metrics — set EVAL_API_URL for live scan scoring",
            "mode": "stub",
        }

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
