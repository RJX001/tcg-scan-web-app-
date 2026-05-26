# TCG Scan

Price guide for trading cards — scan a card, see cross-marketplace comps, condition estimates, and grading ROI.

## Quick start

```bash
pnpm install
docker compose -f infra/docker/docker-compose.yml up -d
uv sync --all-packages
pnpm db:migrate
pnpm db:seed
pnpm dev
```

A local `.env` is included (gitignored) with docker-compose defaults. Copy `.env.example` if missing.

**Dev auth:** With `DEV_AUTH_ENABLED=true` and no Clerk keys, the API accepts `X-Dev-User-Id` (the web SDK sends `dev-user` automatically).

## Weeks 1–5 — catalog + pricing pipeline

```bash
pnpm ingest:catalog -- --game pokemon --limit 500
pnpm embed:catalog -- --game pokemon --limit 500
pnpm catalog:all
pnpm ingest:pricing -- --game pokemon --card-limit 100
pnpm rollup:daily
pnpm worker
pnpm schedules:register
```

## Weeks 6–12 — what ships in this repo

| Week | Feature |
|------|---------|
| 6 | Scan API v0 — detect crop, ANN search, Redis cache, stage timings |
| 7 | OCR re-rank + heuristic condition grader + grade ROI |
| 8 | `/search`, 90d price chart, multi-source tiles, grade ROI panel |
| 9 | Webcam capture, drag-drop upload, game selector, low-confidence confirm |
| 10 | Portfolio + alerts API/pages, dev auth, scan rate limits |
| 11 | LangGraph agents (scan, pricing, grade ROI, monitor, digest) |
| 12 | Eval harness scaffold, beta launch runbook |

## Pages

- `/` — landing
- `/scan` — camera + upload scan
- `/search` — catalog text search
- `/card/[slug]` — comps, chart, ROI
- `/portfolio` — collection tracker
- `/alerts` — price alerts

See [AGENTS.md](./AGENTS.md), [docs/TCG_Scan_Phase1.md](./docs/TCG_Scan_Phase1.md), and [docs/runbooks/beta-launch.md](./docs/runbooks/beta-launch.md).
