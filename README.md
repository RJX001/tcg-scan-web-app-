# TCG Scan — Phase 1 build complete (Weeks 6–12)

Price guide for trading cards — scan a card, see cross-marketplace comps, condition estimates, and grading ROI.

## Quick start

```bash
pnpm install
docker compose -f infra/docker/docker-compose.yml up -d postgres qdrant
uv sync --all-packages
pnpm db:migrate
pnpm db:seed
pnpm dev --filter @tcgscan/web --filter @tcgscan/api
```

Open http://localhost:3000 — demo card: http://localhost:3000/card/pokemon-base1-4-102

## Weeks 6–12 deliverables

| Week | Status | What's shipped |
|------|--------|----------------|
| 6–7 | Done | Scan API: detect/crop, Qdrant ANN, OCR rerank, popularity prior, bbox, condition estimate |
| 8 | Done | Search, card detail (chart, comps, listings, multi-source tiles, grade ROI) |
| 9 | Done | Webcam, drag-drop, game selector, low-confidence confirm, bbox overlay |
| 10 | Done | Portfolio + alerts API/UI, tier gates (10 scans/day, 25 portfolio, alerts=Pro), Stripe checkout scaffold, `/account` |
| 11 | Done | LangGraph agents + pricing tools wired to API; Temporal alert monitor schedule |
| 12 | Done | Eval harness (stub + live via `EVAL_API_URL`), Sentry/OTel hooks, beta runbook |

## Tier model

| Free | Pro ($9.99/mo) |
|------|----------------|
| 10 scans/day | Unlimited scans |
| 25 portfolio cards | Unlimited portfolio |
| Search + public card pages | Price alerts |
| Condition + ROI on scan | Daily digest (agent scaffold) |

Set `STRIPE_PRO_PRICE_ID` + Stripe keys to enable checkout. Dev mode uses `X-Dev-User-Id: dev-user`.

## Production checklist (post-code)

- [ ] Deploy Modal ML endpoints + populate Qdrant with real embeddings
- [ ] Add Clerk keys for production auth
- [ ] Configure Stripe webhook → `/v1/billing/webhook`
- [ ] Run pricing ingest schedules (`pnpm worker`, `pnpm schedules:register`)
- [ ] Closed beta (25 users) per `docs/runbooks/beta-launch.md`

See [AGENTS.md](./AGENTS.md), [docs/TCG_Scan_Phase1.md](./docs/TCG_Scan_Phase1.md), and **[docs/PROJECT_TRACKING.md](./docs/PROJECT_TRACKING.md)** for full status.
