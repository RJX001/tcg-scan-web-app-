# TCG Scan — Project tracking

**Last updated:** May 26, 2026  
**Repo:** `tcg-scan-web-app-`  
**Phase:** Phase 1 (90-day plan) — **code complete for Weeks 6–12**, pre-production wiring

---

## At a glance

| Area | Status | Notes |
|------|--------|--------|
| **Monorepo + infra** | Done | pnpm + Turborepo, Docker (Postgres, Qdrant, Redis), CI |
| **Weeks 1–5** | Partial | Catalog/pricing ingest scripts exist; needs scheduled runs + API keys |
| **Weeks 6–12 (app)** | Done | Scan, search, card detail, portfolio, alerts, billing scaffold |
| **ML (production)** | Not live | Local/Modal **stubs** — real YOLO/DINOv2/OCR not deployed |
| **Auth (production)** | Scaffold | Dev bypass works; Clerk wired when keys present |
| **Payments** | Scaffold | Stripe checkout/portal/webhook coded; needs `STRIPE_*` keys |
| **Beta launch** | Not started | See [runbooks/beta-launch.md](./runbooks/beta-launch.md) |

**Bottom line:** The product **works end-to-end locally** with seed data. Going live requires Modal ML, live pricing ingest, Clerk, and Stripe.

---

## 90-day roadmap (Weeks 1–12)

### Weeks 1–5 — Foundation & data

| Week | Goal | Status | What exists |
|------|------|--------|-------------|
| 1 | Repo + infra | Done | Monorepo, AGENTS.md, docker-compose, CI |
| 2 | Catalog ingest (Pokemon, MTG, YGO) | Partial | `pnpm ingest:catalog`, `pnpm embed:catalog` |
| 3 | Catalog completion + Qdrant | Partial | Lorcana, One Piece, sports modules; Qdrant client |
| 4 | eBay sold + active ingest | Partial | Worker workflows + eBay sources |
| 5 | TCGPlayer + Cardmarket | Partial | Source modules; needs API keys / Apify |

### Weeks 6–12 — Product (shipped in code)

| Week | Goal | Status | What exists |
|------|------|--------|-------------|
| 6 | Scan API v0 | Done | `POST /v1/scan`, Qdrant ANN, cache, `stages_ms` |
| 7 | Scan refinement | Done | OCR rerank, popularity prior, heuristic grader, bbox |
| 8 | Search + card detail | Done | `/search`, `/card/[slug]`, chart, comps, listings, ROI |
| 9 | Scan UX (web) | Done | Webcam, drag-drop, game selector, confirm step, bbox overlay |
| 10 | Auth + portfolio + alerts | Done | Tier gates, portfolio/alerts API + pages, Stripe + `/account` |
| 11 | Agentic layer | Done (scaffold) | LangGraph agents, pricing tools → API, alert monitor workflow |
| 12 | Hardening + beta prep | Done (scaffold) | Eval harness, Sentry/OTel hooks, beta runbook |

---

## Feature checklist (user-facing)

### Working locally (with `pnpm db:seed` + dev servers)

- [x] Landing page — http://localhost:3000
- [x] Card scanner — `/scan` (upload + webcam)
- [x] Catalog search — `/search`
- [x] Card detail — `/card/pokemon-base1-4-102` (chart, comps, listings, ROI)
- [x] Portfolio — add/remove, estimated collection value
- [x] Alerts UI — create/list/delete (Pro-gated on API)
- [x] Account / upgrade UI — `/account`
- [x] API health — http://localhost:8000/v1/health

### Needs production setup

- [ ] Real card matching (Modal embed + populated Qdrant)
- [ ] Live marketplace prices (worker schedules + eBay/TCG keys)
- [ ] Clerk sign-in on web (replace dev header)
- [ ] Stripe checkout + webhook → `users.tier = pro`
- [ ] Email/push when price alerts fire
- [ ] Daily digest email (DigestAgent + Sonnet when `ANTHROPIC_API_KEY` set)

---

## Free vs Pro (planned)

| | Free | Pro ($9.99/mo) |
|---|------|----------------|
| Scans | 10 / day | Unlimited |
| Portfolio | 25 cards | Unlimited |
| Search + public card pages | Yes | Yes |
| Price alerts | No | Yes |
| Daily digest | No | Yes (scaffold) |

**Enforcement:** `FREE_SCANS_PER_DAY`, `FREE_PORTFOLIO_LIMIT` in API; alerts require `tier=pro`.

---

## Key API routes

| Method | Path | Auth | Notes |
|--------|------|------|--------|
| GET | `/v1/health` | Public | Liveness |
| POST | `/v1/scan` | Optional | Rate-limited for free tier |
| GET | `/v1/cards/search` | Public | Text search |
| GET | `/v1/cards/slug/{slug}` | Public | Card detail |
| GET | `/v1/cards/{id}/comps` | Public | Sold comps |
| GET | `/v1/cards/{id}/listings` | Public | Active listings |
| GET | `/v1/cards/{id}/chart` | Public | 90-day chart |
| GET | `/v1/cards/{id}/grade-roi` | Public | GRADE / SELL / HOLD |
| GET/POST | `/v1/portfolio` | Required | Portfolio CRUD |
| GET | `/v1/portfolio/summary` | Required | Collection value |
| GET/POST | `/v1/alerts` | Required | Alerts (create = Pro) |
| GET | `/v1/account` | Required | Tier + limits |
| POST | `/v1/billing/checkout` | Required | Stripe (needs keys) |
| POST | `/v1/billing/webhook` | Stripe sig | Tier sync |

---

## ML & scan accuracy

| Component | Local dev | Production target |
|-----------|-----------|-------------------|
| Detection | Full-frame stub | YOLO on Modal |
| Embeddings | Hash stub | DINOv2/SigLIP 1024-dim |
| OCR | Empty stub | PaddleOCR rerank |
| Condition grade | Heuristic | Trained grader |
| Qdrant index | Manual `embed:catalog` | Full catalog embed |

**Eval:** `pnpm eval` — stub by default; set `EVAL_API_URL=http://localhost:8000` for live scan scoring.

**Phase 1 KPIs (not yet met):** top-1 ≥ 90%, top-5 ≥ 98%, scan p95 &lt; 2.5s.

---

## Database migrations

| Revision | Description |
|----------|-------------|
| `0001_initial` | `card_identity`, `sale_event`, rollups |
| `0002_users_portfolio_alerts` | Users, portfolio, price alerts |
| `0003_stripe_customer` | `users.stripe_customer_id` |

Run: `pnpm db:migrate` · Seed: `pnpm db:seed`

---

## Tests (last known)

| Package | Status |
|---------|--------|
| `@tcgscan/api` | 15 passed |
| `@tcgscan/worker` | Passing |
| `@tcgscan/ml` | 4 passed |
| `@tcgscan/web`, `sdk-ts`, `ui`, `schema` | Passing |

Run: `pnpm test`

---

## Environment & local setup

**Postgres:** port `5433` in docker-compose (avoids conflict with other local Postgres).

**Dev auth:** `DEV_AUTH_ENABLED=true` → header `X-Dev-User-Id: dev-user` (web SDK sends automatically).

**Required for full local demo:**

```bash
docker compose -f infra/docker/docker-compose.yml up -d postgres qdrant
pnpm db:migrate && pnpm db:seed
pnpm dev --filter @tcgscan/web --filter @tcgscan/api
```

Copy `.env.example` → `.env` if missing.

---

## Production go-live checklist

Use this order:

1. [ ] Deploy Modal (`detect`, `embed`, `ocr`, `grade`) — set `MODAL_*_URL` in `.env`
2. [ ] Run catalog ingest + `pnpm embed:catalog` for target games
3. [ ] Configure Clerk (`CLERK_SECRET_KEY`, `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`)
4. [ ] Configure Stripe (`STRIPE_PRO_PRICE_ID`, webhook → `/v1/billing/webhook`)
5. [ ] Start Temporal worker + `pnpm schedules:register`
6. [ ] Enable Sentry / OTel / LangSmith env vars
7. [ ] Mobile QA (Safari + Chrome scan flow)
8. [ ] Closed beta — 25 users ([beta-launch.md](./runbooks/beta-launch.md))

---

## Positioning (marketing)

- **Public copy:** Price guide + scanner — no “AI” in UI
- **Behind the scenes:** embeddings, OCR rerank, condition model, LangGraph agents
- **vs Card Ladder:** Multi-TCG, scan-first, lower Pro price ($9.99 vs ~$20), grading ROI verdict

---

## Related docs

| Doc | Purpose |
|-----|---------|
| [TCG_Scan_Phase1.md](./TCG_Scan_Phase1.md) | Canonical product spec |
| [runbooks/beta-launch.md](./runbooks/beta-launch.md) | Beta gate checklist |
| [AGENTS.md](../AGENTS.md) | Coding agent conventions |
| [README.md](../README.md) | Quick start |

---

## Changelog (tracking)

| Date | Update |
|------|--------|
| 2026-05-26 | Weeks 6–12 code complete: tiers, Stripe scaffold, listings, alert monitor, eval hooks |
| 2026-05-26 | UI copy: removed “AI” from user-facing text |
| 2026-05-26 | Local demo verified (web + API, Charizard seed card) |

---

*Update this file when you ship a milestone, wire a service, or start beta.*
