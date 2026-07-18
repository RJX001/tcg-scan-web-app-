# TCG Scan / TCG Chart — Phase 1

Price guide for trading cards — scan a card, see cross-marketplace comps, condition estimates, and grading ROI.

**Status:** Weeks 1–12 are **code-complete for local demo**. Closed beta and production live pricing still need API keys, Modal weights, and ops setup — see [docs/PROJECT_TRACKING.md](./docs/PROJECT_TRACKING.md) and [docs/runbooks/beta-launch.md](./docs/runbooks/beta-launch.md).

Shipped UI brand: **TCG Chart**. Repo / package name: **TCG Scan**.

## Quick start

```bash
pnpm install
docker compose -f infra/docker/docker-compose.yml up -d postgres qdrant redis
uv sync --all-packages
pnpm db:demo
pnpm dev --filter @tcgscan/web --filter @tcgscan/api
```

Open http://localhost:3000 — demo card: http://localhost:3000/card/pokemon-base1-4-102

Dev auth (no Supabase required locally): `DEV_AUTH_ENABLED=true` + header `X-Dev-User-Id: dev-user` (seed sets Pro / owner).

## Weeks 1–12 deliverables

| Week | Milestone | Status |
|------|-----------|--------|
| 1 | Monorepo + infra (pnpm, Turbo, Docker, CI, AGENTS.md) | Done |
| 2 | Catalog ingest: Pokemon, MTG, Yu-Gi-Oh + embed pipeline | Done (CLI; live needs network) |
| 3 | Lorcana, One Piece, Sports + Qdrant index | Done |
| 4 | eBay active + sold ingest, Temporal workflows, rollups | Done (code; live needs keys) |
| 5 | TCGPlayer + Cardmarket sources, FX normalization | Done (code; live needs keys) |
| 6 | Scan API v0: POST `/v1/scan`, Qdrant ANN, Redis cache | Done (ML stubs without Modal) |
| 7 | OCR rerank, popularity prior, heuristic grader, bbox | Done |
| 8 | Search + card detail (chart, comps, listings, ROI) | Done |
| 9 | Scan UX: webcam, drag-drop, confirm step, bbox overlay | Done (prod-gated by `NEXT_PUBLIC_SCAN_ENABLED`) |
| 10 | Auth tiers, portfolio, alerts, Stripe scaffold, `/account` | Done (**Supabase** Auth + Stripe) |
| 11 | LangGraph agents (Scan, Pricing, GradeROI, Monitor, Digest) | Done (mostly heuristics today) |
| 12 | Eval harness, observability hooks, beta runbook | Done (scaffolds) |

## Commands

| Command | Purpose |
|---------|---------|
| `pnpm db:demo` | Migrate + seed + stub-embed five TCG catalogs into Qdrant |
| `pnpm ingest:catalog -- --game pokemon` | Ingest catalog from official APIs |
| `pnpm embed:catalog -- --game pokemon` | Embed catalog images to Qdrant |
| `pnpm ingest:pricing -- --game pokemon --card-limit 100` | Pull marketplace comps |
| `pnpm schedules:register` | Register Temporal schedules (needs local Temporal or Cloud) |
| `pnpm eval` | ML eval harness (see `apps/ml/eval/README.md`) |

## Tier model

| Free | Pro ($9.99/mo) |
|------|----------------|
| 10 scans/day | Unlimited scans |
| 25 portfolio cards | Unlimited portfolio |
| Search + public card pages | Price alerts + watchlist + saved searches + digest |

## Production checklist (requires your API keys)

- [ ] Deploy Modal ML (`MODAL_*_URL`) + full catalog embed with real vectors
- [ ] Supabase Auth env on web + API (`NEXT_PUBLIC_SUPABASE_*`, `SUPABASE_JWT_SECRET` or `SUPABASE_JWKS_URL`)
- [ ] Stripe (`STRIPE_SECRET_KEY`, `STRIPE_PRO_PRICE_ID`, `STRIPE_WEBHOOK_SECRET`) + webhook to `/v1/billing/webhook`
- [ ] eBay / TCG / Apify keys on the **worker** for live pricing
- [ ] Closed beta per `docs/runbooks/beta-launch.md`

## Docs for new hires

1. [AGENTS.md](./AGENTS.md) — conventions (source of truth for agents)
2. [docs/TCG_Scan_Phase1.md](./docs/TCG_Scan_Phase1.md) — product spec
3. [docs/PROJECT_TRACKING.md](./docs/PROJECT_TRACKING.md) — what’s walkable vs gated
4. [docs/LIVE_DATA_AND_STRIPE_SETUP.md](./docs/LIVE_DATA_AND_STRIPE_SETUP.md) — live data + billing
5. [docs/CLERK_REMOVAL_AND_SUPABASE_AUTH_REPORT.md](./docs/CLERK_REMOVAL_AND_SUPABASE_AUTH_REPORT.md) — auth as-built

**Do not use** `CURSOR_CONTEXT.md` or `CLAUDE_CODE_GUIDE.md` for architecture — they describe an abandoned `backend/` + Celery layout.
