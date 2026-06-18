---
name: run-web
description: Run, start, launch, test, screenshot the Next.js frontend web app
---

# run-web skill

Starts the TCG Scan Next.js 15 frontend and verifies it serves HTTP 200 on the home page.

## Verified environment

- Node 20+, pnpm 9.x
- `pnpm install --prefer-offline` succeeds using the cached packages already in the pnpm store
- `pnpm build` produces a full static+dynamic build (verified 2026-06-18)
- `next start` returns HTTP 200 on `/`

## Quick start

```bash
# From repo root
pnpm install --prefer-offline

# Build (required before `start`; skip for `dev`)
NEXT_PUBLIC_API_URL=http://localhost:8001 \
NEXT_PUBLIC_SUPABASE_URL=http://localhost \
NEXT_PUBLIC_SUPABASE_ANON_KEY=dummy \
  pnpm --filter @tcgscan/web build

# Start (production mode, port 3001 to avoid conflicts)
NEXT_PUBLIC_API_URL=http://localhost:8001 \
NEXT_PUBLIC_SUPABASE_URL=http://localhost \
NEXT_PUBLIC_SUPABASE_ANON_KEY=dummy \
  pnpm --filter @tcgscan/web start --port 3001 &

# Verify it's up
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3001/
```

Or use `dev` mode (no build needed, hot reload):

```bash
NEXT_PUBLIC_API_URL=http://localhost:8001 \
NEXT_PUBLIC_SUPABASE_URL=http://localhost \
NEXT_PUBLIC_SUPABASE_ANON_KEY=dummy \
  pnpm --filter @tcgscan/web dev &
sleep 5 && curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3000/
```

## Screenshot with chromium-cli

```bash
# Take a screenshot of the home page
chromium-cli screenshot http://localhost:3001/ /tmp/web-home.png \
  --window-size=1280,800 2>/dev/null \
  || chromium --headless --screenshot=/tmp/web-home.png \
       --window-size=1280,800 http://localhost:3001/ 2>/dev/null
echo "Screenshot saved to /tmp/web-home.png"
```

## Key env vars

| Variable | Required | Notes |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | Yes | URL of the FastAPI backend (e.g. `http://localhost:8001`) |
| `NEXT_PUBLIC_SUPABASE_URL` | Yes (build-time) | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Yes (build-time) | Supabase anon key |

Create `.env.local` inside `apps/web/` for local overrides — Next.js reads it automatically.

Example `apps/web/.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8001
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

## Gotchas

- **`pnpm install` may hit npm 403**: The full install requires network access to the npm registry. Use `--prefer-offline` to reuse the cached packages already present in the pnpm store (sufficient for normal dev work). If the store is cold, you need registry access.
- **Build before start**: `next start` requires a prior `next build`. Use `pnpm dev` to skip the build step during development.
- **Port conflict**: The default `pnpm dev` uses port 3000. Use `--port 3001` (or another free port) if something else is already bound to 3000.
- **API backend**: Most pages call `NEXT_PUBLIC_API_URL`. The build succeeds with a dummy value, but runtime pages that fetch data will fail without a real backend running.
- **Auth**: Authentication is handled by Supabase. Pages that require login redirect to `/sign-in`. Setting dummy Supabase env vars is fine for build and static page checks; live auth needs real credentials.
