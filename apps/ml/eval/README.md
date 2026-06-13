# ML eval harness

Run scan accuracy and latency benchmarks per `docs/TCG_Scan_Phase1.md` §5.4 and §9.

## Commands

```bash
# Stub metrics (no API required)
pnpm eval

# Live scoring against local API
EVAL_API_URL=http://localhost:8000 pnpm eval
```

## Fixture format

`apps/ml/eval/fixtures/sample.csv`:

```csv
image_path,true_card_id,true_grade
fixtures/charizard.jpg,11111111-1111-4111-8111-111111111111,8
```

Add held-out photos under `apps/ml/eval/fixtures/` before claiming KPI gates.

## KPI gates (Phase 1)

| Metric | Target |
|--------|--------|
| top-1 accuracy | ≥ 90% |
| top-5 accuracy | ≥ 98% |
| scan p95 latency | &lt; 2.5s |
| condition MAE | report only |

Reports write to `apps/ml/eval/reports/latest.json`.
