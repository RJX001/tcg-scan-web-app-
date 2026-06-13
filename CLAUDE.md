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
