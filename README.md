# TCG Scan — Phase 1 (Weeks 1–12 complete)

Price guide for trading cards — scan a card, see cross-marketplace comps, condition estimates, and grading ROI.

## Quick start

```bash
pnpm install
docker compose -f infra/docker/docker-compose.yml up -d postgres qdrant redis
uv sync --all-packages
pnpm db:demo
pnpm dev --filter @tcgscan/web --filter @tcgscan/api
```

Open http://localhost:3000 — demo card: http://localhost:3000/card/pokemon-base1-4-102

## Weeks 1–12 deliverables

| Week | Milestone | Status |
|------|-----------|--------|
| 1 | Monorepo + infra (pnpm, Turbo, Docker, CI, AGENTS.md) | Done |
| 2 | Catalog ingest: Pokemon, MTG, Yu-Gi-Oh + embed pipeline | Done (CLI; run with API keys) |
| 3 | Lorcana, One Piece, Sports + Qdrant index | Done |
| 4 | eBay active + sold ingest, Temporal workflows, rollups | Done |
| 5 | TCGPlayer + Cardmarket sources, FX normalization | Done |
| 6 | Scan API v0: POST `/v1/scan`, Qdrant ANN, Redis cache | Done |
| 7 | OCR rerank, popularity prior, heuristic grader, bbox | Done |
| 8 | Search + card detail (chart, comps, listings, ROI) | Done |
| 9 | Scan UX: webcam, drag-drop, confirm step, bbox overlay | Done |
| 10 | Auth tiers, portfolio, alerts, Stripe scaffold, `/account` | Done |
| 11 | LangGraph agents (Scan, Pricing, GradeROI, Monitor, Digest) | Done |
| 12 | Eval harness, observability hooks, beta runbook | Done |

## Commands

| Command | Purpose |
|---------|---------|
| `pnpm db:demo` | Migrate + seed + embed Pokemon into Qdrant |
| `pnpm ingest:catalog -- --game pokemon` | Ingest catalog from official APIs |
| `pnpm embed:catalog -- --game pokemon` | Embed catalog images to Qdrant |
| `pnpm ingest:pricing -- --game pokemon --card-limit 100` | Pull marketplace comps |
| `pnpm schedules:register` | Register Temporal schedules (needs worker) |
| `pnpm eval` | ML eval harness (see `apps/ml/eval/README.md`) |

## Tier model

| Free | Pro ($9.99/mo) |
|------|----------------|
| 10 scans/day | Unlimited scans |
| 25 portfolio cards | Unlimited portfolio |
| Search + public card pages | Price alerts + daily brief |

Dev mode: `DEV_AUTH_ENABLED=true` + header `X-Dev-User-Id: dev-user` (seed sets Pro tier).

## Production checklist (requires your API keys)

- [ ] Deploy Modal ML (`MODAL_*_URL`) + full catalog embed
- [ ] Clerk keys + Stripe webhook
- [ ] eBay / TCG / Apify keys for live pricing
- [ ] Closed beta per `docs/runbooks/beta-launch.md`

See [AGENTS.md](./AGENTS.md), [docs/TCG_Scan_Phase1.md](./docs/TCG_Scan_Phase1.md), [docs/PROJECT_TRACKING.md](./docs/PROJECT_TRACKING.md).
