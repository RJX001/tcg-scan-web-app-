# CLAUDE.md — TCG Scan / TCG Chart repo conventions

Read **AGENTS.md** first. Canonical product spec: **docs/TCG_Scan_Phase1.md**.

Shipped UI brand: **TCG Chart**. Package / docs name: **TCG Scan**.

## Architecture (locked)

Monorepo: `pnpm` + Turborepo + `uv`.

| App / package | Role |
|---|---|
| `apps/web` | Next.js 15 (App Router) |
| `apps/api` | FastAPI `/v1` |
| `apps/worker` | Temporal worker (catalog, pricing, rollup, alerts, digest) |
| `apps/ml` | Modal endpoints (detect / embed / ocr / grade) |
| `packages/sdk-ts` | TypeScript API client (hand-maintained until OpenAPI codegen lands) |
| `packages/sdk-py` | Internal Python client |
| `packages/schema` | Shared JSON Schema scaffolds |
| `packages/ui` | Shared React components |
| `packages/agents` | LangGraph graphs |

**Data:** Postgres 16 + pgvector (app OLTP — local Docker / Railway). **Auth:** Supabase Auth (JWT only; not the app DB). Qdrant (image embeddings). Redis (cache / rate limits). **Payments:** Stripe. **Agents:** LangGraph (+ Claude when wired).

**One rule:** `apps/web` never calls eBay, TCGPlayer, Cardmarket, or other marketplaces. External data → worker (or admin ingest on the API) → Postgres. Web → our API only (`NEXT_PUBLIC_API_URL`).

## Commands

```bash
pnpm install
docker compose -f infra/docker/docker-compose.yml up -d postgres qdrant redis
uv sync --all-packages
pnpm db:demo
pnpm dev --filter @tcgscan/web --filter @tcgscan/api

pnpm lint && pnpm typecheck && pnpm test
pnpm schema:build     # after schema package changes
pnpm sdk:generate     # placeholder until OpenAPI codegen is wired
```

## Auth (current)

- Web: Supabase SSR (`@supabase/ssr`) + middleware on protected routes.
- API: `AuthMiddleware` verifies Supabase JWT (`SUPABASE_JWT_SECRET` or `SUPABASE_JWKS_URL`).
- Dev: `DEV_AUTH_ENABLED=true` + `X-Dev-User-Id` (blocked when `ENVIRONMENT=production`).
- Clerk is **removed** — see `docs/CLERK_REMOVAL_AND_SUPABASE_AUTH_REPORT.md`.

## Key product rules

- eBay links should include EPN affiliate tags when `EBAY_AFFILIATE_*` is set.
- Prefer ≥5 sales before treating comps as a solid market value (UI gates thin data).
- Free tier: 10 scans/day, 25 portfolio cards; Pro gates alerts, watchlist, saved searches, digest.
- Pro gating is enforced on the **API** (`require_pro`, scan rate limits). Web shows soft upgrade copy.

## Data sources (as-built)

| Source | Status | Notes |
|---|---|---|
| eBay Browse API | Implemented | Needs production keys + Account Deletion compliance |
| eBay Insights (sold) | Optional | Falls back to Browse without `EBAY_INSIGHTS_TOKEN` |
| Scryfall / PTCGIO / YGOPRODECK / Lorcast / OPTCG | Implemented | Catalog clients in API + worker |
| TCGPlayer (via tcgapi.dev) | Implemented | Needs `TCG_API_KEY` |
| Cardmarket (Apify) | Partial | Dataset poll; needs `APIFY_TOKEN` |
| Reddit | Not implemented | |
| eBay HTML scraping | Forbidden | Use Browse / Insights only |
| TCGplayer direct scrape | Forbidden | Use aggregator API |

## Status honesty

Local demo (`pnpm db:demo`) is walkable. Closed beta still needs Modal weights, live ingest keys, Stripe webhook in prod, and KPI gates — see `docs/runbooks/beta-launch.md` and `docs/PROJECT_TRACKING.md`.

## Obsolete files (do not follow)

- `CURSOR_CONTEXT.md` — abandoned `backend/` + Celery sketch
- `CLAUDE_CODE_GUIDE.md` — same obsolete layout
- Historical Clerk→Supabase migration write-ups under `docs/SUPABASE_AUTH_*` (migration complete)

## Slash commands

See `.cursor/commands.md` (or `cursor_commands.md`) for `/bootstrap`, `/scaffold-endpoint`, `/new-agent`, etc.
