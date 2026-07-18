# TCG Scan / TCG Chart — Project tracking

**Last updated:** July 18, 2026  
**Phase:** Phase 1 Weeks 1–12 — **code complete for local demo**; production keys + beta KPIs pending

---

## At a glance

| Area | Status | Notes |
|------|--------|--------|
| **Week 1** | Done | Monorepo, Docker, CI, AGENTS.md |
| **Weeks 2–5** | Done (CLI) | Catalog + pricing ingest coded; live data needs API keys |
| **Weeks 6–12** | Done (demo) | Full web app + API + agent scaffolds + eval harness |
| **ML production** | Stub | Modal deploy + real weights required for scan KPI gates |
| **Auth** | Supabase | Clerk removed; JWT middleware + web SSR clients |
| **Payments** | Scaffold | Stripe checkout/portal/webhook coded; prod keys + hardening pending |
| **Beta launch** | Not started | `docs/runbooks/beta-launch.md` |

**Bottom line:** Run `pnpm db:demo` + `pnpm dev` for a full **offline** walkthrough on seed data. Production go-live needs Modal, marketplace keys on the worker, Supabase, and Stripe.

UI brand ships as **TCG Chart**; docs/package name remains **TCG Scan**.

---

## Week-by-week (Phase 1 §8)

| Week | Goal | Status | Key paths |
|------|------|--------|-----------|
| 1 | Repo + infra | Done | `turbo.json`, `infra/docker/`, `.github/workflows/` |
| 2 | Catalog ingest (Pokemon, MTG, YGO) | Done | `apps/worker/.../catalog/`, `pnpm ingest:catalog` |
| 3 | Catalog + Qdrant | Done | lorcana, one_piece, sports, `embedding.py` |
| 4 | eBay sold + active | Done | `sources/ebay_*.py`, `workflows/ebay_workflow.py` |
| 5 | TCGPlayer + Cardmarket | Done | `sources/tcgplayer.py`, `cardmarket.py` |
| 6 | Scan API v0 | Done | `apps/api/.../routes/scan.py`, `services/scan.py` |
| 7 | Scan refinement | Done | OCR rerank, heuristic grader, bbox, catalog fallback |
| 8 | Search + card detail | Done | `apps/web/src/app/search`, `card/[slug]` |
| 9 | Scan UX | Done | `apps/web/src/app/scan/scan-form.tsx` |
| 10 | Auth + portfolio + alerts | Done | **Supabase** + Stripe + portfolio CSV |
| 11 | Agentic layer | Done | `packages/agents` (heuristics / API wrappers today) |
| 12 | Hardening | Done | `apps/ml/eval/`, telemetry hooks, beta runbook |

---

## Feature checklist

### Works locally (`pnpm db:demo` + dev servers)

- [x] Landing, scan, search (text + image), card detail
- [x] Charts, comps, listings, grade ROI, PSA pop link (seed / thin-data messaging when empty)
- [x] Portfolio + CSV export, alerts CRUD, account/billing UI
- [x] Daily brief preview (`/digest`) — soft / Pro-gated
- [x] Admin + sources ops (`/admin`, `/admin/sources`)
- [x] API surface — see `apps/api/docs/endpoints.md`

### Requires production setup

- [ ] Real scan accuracy (Modal ML + full Qdrant index with real embeddings)
- [ ] Live marketplace prices (worker ingest schedules + eBay / TCG / Apify keys)
- [ ] Supabase sign-in on web (prod env vars)
- [ ] Stripe live checkout + verified webhook
- [ ] Alert email/push delivery (monitor marks triggers; delivery not shipped)
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

## Doc drift notes (for agents / new hires)

| Trust | Ignore for architecture |
|-------|-------------------------|
| `AGENTS.md`, this file, `README.md` | `CURSOR_CONTEXT.md` (Celery / `backend/`) |
| `docs/LIVE_DATA_*`, Supabase auth reports | Conflicted/obsolete Celery guides |
| `apps/*/AGENTS.md` | Historical `docs/SUPABASE_AUTH_MIGRATION_GUIDE.md` steps (migration done) |

---

## Changelog (tracking)

| Date | Update |
|------|--------|
| 2026-07-18 | Docs sync: Supabase (not Clerk), Temporal (not Celery), demo vs beta honesty |
| 2026-05-31 | Weeks 1–12 audit complete: comps filter, PSA pop link, eval README, test fix, docs sync |
| 2026-05-31 | Agents wired, image search, portfolio CSV, `pnpm db:demo` |
| 2026-05-26 | Initial Weeks 6–12 product slice |

---

*Update when wiring production services or starting beta.*
