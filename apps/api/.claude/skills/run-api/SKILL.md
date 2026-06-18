---
name: run-api
description: Run, start, launch, test, screenshot the FastAPI backend API server
---

# run-api skill

Starts the TCG Scan FastAPI backend, smoke-tests it with curl, and reports the result.

## Verified environment

- Python 3.12 required (repo requires `>=3.12`)
- A `.venv312` virtualenv at the **repo root** (`/home/user/tcg-scan-web-app-/.venv312`) was created and verified working

## Quick start

```bash
# From repo root — install all Python workspace packages once
python3.12 -m venv .venv312
.venv312/bin/pip install \
  -e packages/agents \
  -e packages/sdk-py \
  -e apps/ml \
  -e apps/api

# Start the server (port 8001 to avoid conflicts)
ENVIRONMENT=development \
  .venv312/bin/uvicorn tcgscan_api.main:app \
    --app-dir apps/api \
    --port 8001 \
    --reload &

# Smoke test
bash apps/api/.claude/skills/run-api/smoke.sh
```

## What the smoke test checks

| Endpoint | Expected |
|---|---|
| `GET /v1/health` | `{"status":"ok","version":"0.0.0"}` — HTTP 200 |

Run `bash apps/api/.claude/skills/run-api/smoke.sh` (or `API_URL=http://localhost:8001 bash ...`).

## Key env vars

| Variable | Default | Notes |
|---|---|---|
| `ENVIRONMENT` | `development` | Set to `production` to enforce Supabase JWT auth |
| `DATABASE_URL` | `postgresql+asyncpg://tcgscan:tcgscan@localhost:5432/tcgscan` | Postgres 16 |
| `REDIS_URL` | `redis://localhost:6379` | |
| `QDRANT_URL` | `http://localhost:6333` | |
| `SUPABASE_JWT_SECRET` | *(none)* | Required in production |
| `SUPABASE_JWKS_URL` | *(none)* | Alternative to JWT secret |
| `EBAY_APP_ID` | *(none)* | eBay Browse API credential |
| `STRIPE_SECRET_KEY` | *(none)* | Stripe integration |
| `ANTHROPIC_API_KEY` | *(none)* | AI agents (guarded by `ENABLE_AI_AGENTS`) |

Put non-secret defaults in `.env` at the repo root — `pydantic-settings` reads it automatically.

## Docker services (Postgres, Redis, Qdrant)

```bash
docker compose up -d
```

The API will start without them in development mode (DB errors are deferred until a route is called).

## Gotchas

- **Python version**: The project requires Python 3.12+. The system default may be 3.11 — use the `.venv312` venv explicitly.
- **Workspace packages**: `tcgscan-agents`, `tcgscan-sdk-py`, and `tcgscan-ml` must all be installed from source before `tcgscan-api`; `pip install -e apps/api` alone will fail.
- **DB on startup**: The server starts successfully without a running Postgres instance. Connection errors only surface when a DB-backed route is called.
- **Auth in dev**: `DEV_AUTH_ENABLED=true` (the default) allows unauthenticated requests in development — safe to test without Supabase tokens.
- **Module path**: uvicorn must use `tcgscan_api.main:app` (the package name), not `app.main:app`. Pass `--app-dir apps/api` so the package is importable.
