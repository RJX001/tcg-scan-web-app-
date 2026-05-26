# TCG Scan

AI-native price intelligence for trading cards — scan a card, see cross-marketplace comps, condition grade, and grading ROI.

## Quick start

```bash
pnpm install
docker compose -f infra/docker/docker-compose.yml up -d
uv sync
pnpm db:migrate
pnpm db:seed
pnpm dev
```

## Weeks 1–5 pipeline (catalog + pricing)

```bash
# Week 2–3: ingest catalogs + embed to Qdrant
pnpm ingest:catalog -- --game pokemon --limit 500
pnpm embed:catalog -- --game pokemon --limit 500
# Or all games:
pnpm catalog:all

# Week 4–5: ingest marketplace comps (requires API keys in .env)
pnpm ingest:pricing -- --game pokemon --card-limit 100
pnpm rollup:daily

# Temporal worker + schedules (requires Temporal in docker-compose)
pnpm worker
pnpm schedules:register
```

See [AGENTS.md](./AGENTS.md), [docs/TCG_Scan_Phase1.md](./docs/TCG_Scan_Phase1.md), and [docs/data-sources.md](./docs/data-sources.md).
