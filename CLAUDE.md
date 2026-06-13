<<<<<<< Updated upstream
# CLAUDE.md — TCG Scan repo conventions

Read **AGENTS.md** first. Canonical product spec: **docs/TCG_Scan_Phase1.md**.

## Architecture (locked)

Monorepo: `pnpm` + Turborepo. Apps: `web` (Next.js 15), `api` (FastAPI), `worker` (Temporal), `ml` (Modal). Packages: `schema`, `sdk-ts`, `sdk-py`, `ui`, `agents`.

Data: Postgres 16 (+ pgvector), Qdrant (image embeddings), Redis. Auth: Clerk. Payments: Stripe. Agents: LangGraph + Claude. No sync Python HTTP (`requests`/`psycopg2`). No secrets in git.

## Commands

```bash
pnpm dev              # all apps
pnpm lint && pnpm typecheck && pnpm test
pnpm schema:build     # after schema changes
pnpm sdk:generate     # after API OpenAPI changes
```

## Slash commands

See `.cursor/commands.md` for `/bootstrap`, `/scaffold-endpoint`, `/new-agent`, etc.
=======
# TCG Scan Phase 1

AI-native price intelligence for TCG collectors. CardLadder competitor, TCG-focused.
Phase 1: web-only. Phase 2: TCG Vault vendor SaaS (not in scope yet).

## Commands

### Backend
```bash
cd backend
poetry install                        # install dependencies
docker compose up -d                  # start Postgres + PgBouncer + Redis
poetry run alembic upgrade head       # run migrations (seeds 5 games + 17 grades)
poetry run uvicorn app.main:app --reload --port 8000
poetry run pytest -x                  # run tests
poetry run pytest tests/test_health.py  # run single test file
poetry run ruff check app             # lint
poetry run mypy app                   # type check
```

### Frontend
```bash
cd frontend
pnpm install
pnpm dev                              # runs on http://localhost:3000
pnpm build                            # production build
pnpm type-check                       # tsc --noEmit
pnpm lint
```

### Docker services
```bash
docker compose up -d                  # start all services
docker compose ps                     # check status
docker compose logs celery            # celery worker logs
```

### Celery
```bash
cd backend
poetry run celery -A app.tasks.celery_app worker --loglevel=info
poetry run celery -A app.tasks.celery_app beat --loglevel=info
```

## Architecture — THE ONE RULE

The frontend NEVER calls eBay, TCGplayer, Cardmarket or any external API.
- External data → Celery tasks in `backend/app/sources/` → PostgreSQL
- Frontend → our FastAPI only (`NEXT_PUBLIC_API_URL`)

## Project Structure

```
backend/app/
  api/v1/routes/     route handlers (read from DB only)
  services/          business logic
  repositories/      DB query layer
  models/            SQLAlchemy 2 models
  schemas/           Pydantic v2 request/response
  agents/            LangGraph AI agents (4 agents)
  tasks/             Celery tasks (the only place that calls external APIs)
  sources/           external data sources
    ebay/            official Browse API only
    tcgapis/         paid aggregator (subscribe at £500 MRR)
    cardmarket_scraper/  Apify stopgap, max 500/day, disabled by default
    catalogue/       free APIs: Scryfall, PTCGIO, YGOPRODECK
    reddit/          sentiment signals
  core/              config, auth, cache, limiter

frontend/src/
  app/               Next.js 14 App Router pages
  lib/api/           API clients (one per resource, calls OUR backend only)
  components/        Nav, ProGate, Skeleton, QueryProvider
  hooks/             useSubscription, useCards, usePortfolio, useMarket
  stores/            Zustand auth store
  styles/            design tokens (never hardcode colours)
```

## Key Constraints

- Python 3.11 — type hints everywhere
- SQLAlchemy 2 ORM only — never raw SQL
- Alembic for all schema changes — never ALTER TABLE manually
- PgBouncer on port 6432 — not Postgres directly on 5432
- All AI agents gated by `ENABLE_AI_AGENTS=false` env var
- AI agent model: `claude-sonnet-4-6` — never change without instruction
- eBay links must include EPN affiliate tag — never return raw eBay URLs
- Minimum 5 sales before showing TCG Value — show "Insufficient data" otherwise
- Free tier: 10 portfolio cards, 5 alerts, Market Pulse summary only
- Both frontend (useSubscription hook) AND backend (check_subscription_tier) enforce Pro gating

## Data Sources — Risk Rules

| Source | Status | Notes |
|---|---|---|
| eBay Browse API | ACTIVE | Official, 5k calls/day free |
| Scryfall / PTCGIO / YGOPRODECK | ACTIVE | Free catalogues |
| Reddit API | ACTIVE | Official, free with auth |
| Cardmarket (Apify) | STOPGAP | Max 500/day, disabled by default |
| TCGAPIs (paid) | NOT YET | Subscribe at £500 MRR |
| eBay HTML scraping | FORBIDDEN | Use Browse API instead |
| TCGplayer direct | FORBIDDEN | eBay-owned, use TCGAPIs |

## Sprint 1 — Start Here

Implement the three free catalogue sources:
1. `PokemonTcgIOClient.fetch_all_cards()` in `backend/app/sources/catalogue/__init__.py`
2. `ScryfallClient.fetch_all_cards()` in the same file
3. `YgoProDeckClient.fetch_all_cards()` in the same file

Then wire the eBay Browse API in `backend/app/sources/ebay/__init__.py`.
Then implement `compute_tcg_values()` in `backend/app/tasks/compute_values.py`.

See `CURSOR_CONTEXT.md` for the full sprint map and all endpoint details.
>>>>>>> Stashed changes
