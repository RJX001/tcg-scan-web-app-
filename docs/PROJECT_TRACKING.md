# TCG Scan — Project tracking

**Last updated:** May 31, 2026  
**Phase:** Phase 1 Weeks 1–12 — **code complete** (local demo ready; production keys pending)

---

## At a glance

| Area | Status | Notes |
|------|--------|--------|
| **Week 1** | Done | Monorepo, Docker, CI, AGENTS.md |
| **Weeks 2–5** | Done (CLI) | Catalog + pricing ingest; needs API keys for live data |
| **Weeks 6–12** | Done | Full web app + API + agents + eval scaffold |
| **ML production** | Stub | Modal deploy + real weights required for KPI gates |
| **Auth / payments** | Scaffold | Clerk + Stripe coded; dev bypass for local |
| **Beta launch** | Not started | `docs/runbooks/beta-launch.md` |

**Bottom line:** Run `pnpm db:demo` + `pnpm dev` for a full local walkthrough. Production go-live needs Modal, marketplace keys, Clerk, Stripe.

---

## Week-by-week (Phase 1 §8)

| Week | Goal | Status | Key paths |
|------|------|--------|-----------|
| 1 | Repo + infra | Done | `turbo.json`, `infra/docker/`, `.github/workflows/` |
| 2 | Catalog ingest (Pokemon, MTG, YGO) | Done | `worker/catalog/{pokemon,mtg,yugioh}.py`, `pnpm ingest:catalog` |
| 3 | Catalog + Qdrant | Done | `lorcana`, `one_piece`, `sports`, `embedding.py` |
| 4 | eBay sold + active | Done | `sources/ebay_*.py`, `workflows/ebay_workflow.py` |
| 5 | TCGPlayer + Cardmarket | Done | `sources/tcgplayer.py`, `cardmarket.py`, `pricing/fx.py` |
| 6 | Scan API v0 | Done | `api/routes/scan.py`, `services/scan.py`, `services/qdrant.py` |
| 7 | Scan refinement | Done | OCR rerank, heuristic grader, bbox, catalog fallback |
| 8 | Search + card detail | Done | `web/app/search`, `web/app/card/[slug]`, comps filter |
| 9 | Scan UX | Done | `web/app/scan/scan-form.tsx` |
| 10 | Auth + portfolio + alerts | Done | tiers, Stripe, portfolio CSV export |
| 11 | Agentic layer | Done | `packages/agents/*`, monitor + digest workflows |
| 12 | Hardening | Done | `apps/ml/eval/`, telemetry, beta runbook, 17 API tests |

---

## Feature checklist

### Works locally (`pnpm db:demo` + dev servers)

- [x] Landing, scan, search (text + image), card detail
- [x] 90-day chart, comps (filterable), listings, grade ROI, PSA pop link
- [x] Portfolio + CSV export, alerts CRUD, account/billing UI
- [x] Daily brief preview (`/digest`)
- [x] API: 24 routes — see `apps/api/docs/endpoints.md`

### Requires production setup

- [ ] Real scan accuracy (Modal ML + full Qdrant index)
- [ ] Live marketplace prices (ingest schedules + keys)
- [ ] Clerk sign-in on web
- [ ] Stripe live checkout
- [ ] Alert email/push delivery
- [ ] §9 KPIs: top-1 ≥90%, p95 &lt;2.5s

---

## Local setup

```bash
docker compose -f infra/docker/docker-compose.yml up -d postgres qdrant redis
pnpm db:demo
pnpm dev --filter @tcgscan/web --filter @tcgscan/api
```

- Web: http://localhost:3000  
- API: http://localhost:8000/v1/health  
- Postgres: port **5433** (see `docs/data-sources.md`)

---

## Tests (May 31, 2026)

Run: `pnpm test` — all packages green when Postgres not required by integration tests.

---

## Changelog (tracking)

| Date | Update |
|------|--------|
| 2026-05-31 | Weeks 1–12 audit complete: comps filter, PSA pop link, eval README, test fix, docs sync |
| 2026-05-31 | Agents wired, image search, portfolio CSV, `pnpm db:demo` |
| 2026-05-26 | Initial Weeks 6–12 product slice |

---

*Update when wiring production services or starting beta.*
