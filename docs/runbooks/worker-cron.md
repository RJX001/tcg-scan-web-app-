# Worker cron deployment (launch mode)

Temporal workflows remain in the codebase for scale later. For initial production,
run ingestion via **Railway/Render cron jobs** using `apps/worker/Dockerfile` — no
Temporal server required.

## Recommended schedule (UTC)

| Cron | Command |
|------|---------|
| Daily 02:00 | `python -m tcgscan_worker ingest:pricing --game pokemon` |
| Daily 02:15 | `python -m tcgscan_worker ingest:pricing --game mtg` |
| Daily 02:30 | `python -m tcgscan_worker ingest:pricing --game yugioh` |
| Daily 04:00 | `python -m tcgscan_worker rollup:daily` |
| Weekly Sun 03:00 | `python -m tcgscan_worker ingest:catalog --game pokemon` |

Repeat `ingest:catalog` per game as catalog grows. Add `embed:catalog` after Modal
embed endpoints are live.

## Environment

Same as API where overlapping: `DATABASE_URL`, `REDIS_URL`, `QDRANT_*`, eBay keys,
`EBAY_MARKETPLACE_ID=EBAY_GB` (UK-first), `TCG_API_KEY`, etc.

## Temporal (optional)

`python -m tcgscan_worker worker` + `schedules:register` when Temporal Cloud is
provisioned. CLI commands above never require Temporal.
