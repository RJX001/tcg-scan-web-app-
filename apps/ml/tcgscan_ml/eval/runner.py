"""Eval harness — top-1/top-5, condition MAE, latency percentiles."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path


def _load_fixture(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


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
    args = parser.parse_args(argv)

    rows = _load_fixture(Path(args.fixture))
    if not rows:
        report = {
            "status": "skipped",
            "message": "No fixture rows — add eval/fixtures/sample.csv with image_path,true_card_id,true_grade",
            "top1_accuracy": None,
            "top5_accuracy": None,
            "condition_mae": None,
            "latency_p50_ms": None,
            "latency_p95_ms": None,
        }
    else:
        # Stub scorer — replace with live scan pipeline in CI when GPU fixture set exists
        latencies = [120.0 + i * 5 for i in range(len(rows))]
        report = {
            "status": "ok",
            "samples": len(rows),
            "top1_accuracy": 0.0,
            "top5_accuracy": 0.0,
            "condition_mae": 1.5,
            "latency_p50_ms": statistics.median(latencies),
            "latency_p95_ms": sorted(latencies)[int(len(latencies) * 0.95) - 1],
            "note": "Stub metrics until held-out photo set is labeled",
        }

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
