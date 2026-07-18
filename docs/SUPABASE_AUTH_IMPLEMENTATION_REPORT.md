# Supabase Auth Implementation Report

> **Historical.** Migration complete. For current auth behaviour see `AGENTS.md` and `docs/CLERK_REMOVAL_AND_SUPABASE_AUTH_REPORT.md`.

Branch: `supabase-auth-migration`  
Date: 2026-06-15

## Summary

Replaced Clerk with Supabase Auth for sign-in/sign-up, session management, route protection, and API Bearer token verification. Railway PostgreSQL remains the application database. **Clerk has been fully removed** — see [Clerk fully removed](#clerk-fully-removed) below.

## Files changed

### Documentation

- `docs/SUPABASE_AUTH_MIGRATION_GUIDE.md` — migration guide (source of truth)
- `docs/SUPABASE_AUTH_AUDIT.md` — Clerk usage audit checklist

### Frontend (`apps/web`)

| File | Change |
|------|--------|
| `src/lib/supabase/browser.ts` | Browser Supabase client (`createBrowserClient`) |
| `src/lib/supabase/server.ts` | Server Supabase client (`createServerClient` + cookies) |
| `src/lib/supabase/middleware.ts` | Session refresh helper for middleware |
| `src/middleware.ts` | Supabase auth + protected route redirects |
| `src/app/layout.tsx` | Removed `ClerkProvider`; `SupabaseAuthBridge` |
| `src/components/auth-bridge.tsx` | `SupabaseAuthBridge` — injects access token into SDK |
| `src/components/auth-nav.tsx` | Sign in / Account / Sign out based on Supabase session |
| `src/components/dev-banner.tsx` | Supabase-aware local dev banner |
| `src/app/sign-in/page.tsx` | Email/password sign-in |
| `src/app/sign-in/sign-in-form.tsx` | Sign-in form (Suspense-safe) |
| `src/app/sign-up/page.tsx` | Email/password sign-up |
| `src/app/auth/callback/route.ts` | OAuth / email confirmation callback |
| `src/app/sign-out/route.ts` | Sign out + redirect home |
| `src/app/sign-in/[[...sign-in]]/page.tsx` | **Deleted** (Clerk) |
| `src/app/sign-up/[[...sign-up]]/page.tsx` | **Deleted** (Clerk) |
| `package.json` | Added `@supabase/supabase-js`, `@supabase/ssr` |

### Backend (`apps/api`)

| File | Change |
|------|--------|
| `tcgscan_api/middleware/auth.py` | Supabase JWT verify (JWKS + HS256) only |
| `tcgscan_api/config.py` | Supabase settings only |
| `tcgscan_api/main.py` | Production requires Supabase JWT config |
| `tcgscan_api/db/models.py` | `supabase_user_id`; `clerk_id` removed |
| `tcgscan_api/repositories/users.py` | `get_or_create(supabase_user_id=...)` + email linking |
| `tcgscan_api/services/auth_ctx.py` | Resolve DB user by Supabase id |
| `tcgscan_api/services/billing.py` | `AccountOut.supabase_user_id`; Stripe metadata |
| `tcgscan_api/middleware/rate_limit.py` | Rate limit key uses `supabase_user_id` |
| `alembic/versions/0008_supabase_user_id.py` | Adds `supabase_user_id` |
| `alembic/versions/0009_drop_clerk_id.py` | **Drops `clerk_id` column** |
| `pyproject.toml` | `pyjwt`, `cryptography`; removed `clerk-backend-api` |
| Tests | Clear Supabase env in dev-auth tests |

### Shared

- `.env.example` — Supabase vars only; Clerk removed
- `packages/sdk-ts/src/index.ts` — `AccountOut.supabase_user_id`
- `vercel.json` — Clerk CSP domains removed
- `pnpm-lock.yaml`, `uv.lock`

## Clerk fully removed

See also `docs/CLERK_REMOVAL_AND_SUPABASE_AUTH_REPORT.md`.

| Item | Status |
|------|--------|
| `@clerk/nextjs` frontend package | Removed |
| `clerk-backend-api` backend package | Removed |
| Clerk JWT fallback in auth middleware | Removed |
| Clerk env vars in `.env.example` | Removed |
| Active code imports Clerk | None |
| `users.clerk_id` DB column | **Dropped** via migration `0009_drop_clerk_id` |

### Final verification commands (Clerk removal commit)

```powershell
pnpm --filter @tcgscan/web build
pnpm typecheck
cd apps/api && uv run pytest -q
rg -n -S -i "clerk|@clerk|CLERK_|clerk_id|_verify_clerk_bearer" apps packages pyproject.toml package.json pnpm-lock.yaml uv.lock .env.example vercel.json --glob "!**/node_modules/**" --glob "!**/.next/**" --glob "!docs/**"
```

## Migration

**Alembic:** `0008_supabase_user_id` then `0009_drop_clerk_id`

```bash
pnpm db:migrate
```

- `0008` — adds `users.supabase_user_id`, makes `clerk_id` nullable
- `0009` — drops `users.clerk_id` and its index

## Env vars — Vercel (frontend)

| Variable | Required | Notes |
|----------|----------|-------|
| `NEXT_PUBLIC_SUPABASE_URL` | Yes | From Supabase project settings |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Yes | Public anon key |
| `NEXT_PUBLIC_API_URL` | Yes | Railway API URL (unchanged) |
| `NEXT_PUBLIC_SITE_URL` | Yes | e.g. `https://www.cardchart.co.uk` |

Clerk env vars are no longer used. Remove any `CLERK_*` / `NEXT_PUBLIC_CLERK_*` from Vercel and Railway dashboards.

## Env vars — Railway (backend)

| Variable | Required | Notes |
|----------|----------|-------|
| `SUPABASE_URL` | Yes | Same project URL as frontend |
| `SUPABASE_ANON_KEY` | Yes | For consistency; JWT verify uses secret/JWKS |
| `SUPABASE_JWT_SECRET` | Yes* | HS256 projects — from Supabase API settings |
| `SUPABASE_JWKS_URL` | Yes* | Preferred for asymmetric keys: `https://<ref>.supabase.co/auth/v1/.well-known/jwks.json` |
| `DATABASE_URL` | Yes | Railway Postgres (unchanged) |
| `ENVIRONMENT` | Yes | `production` |

\* At least one of `SUPABASE_JWT_SECRET` or `SUPABASE_JWKS_URL` required in production.

Optional:

- `SUPABASE_SERVICE_ROLE_KEY` — admin tasks only; never expose to frontend

## Supabase dashboard setup

1. Enable Email + Password auth.
2. Site URL: `https://www.cardchart.co.uk`
3. Redirect URLs:
   - `https://www.cardchart.co.uk/auth/callback`
   - `https://cardchart.co.uk/auth/callback`
   - `http://localhost:3000/auth/callback`
   - Vercel preview URLs during branch testing
4. Copy JWT secret from Project Settings → API (for HS256) or use JWKS URL.

## How to test locally

1. Create Supabase project; copy URL, anon key, JWT secret.
2. Add to root `.env` / `apps/web/.env.local`:

   ```env
   NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
   NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
   SUPABASE_URL=https://xxx.supabase.co
   SUPABASE_ANON_KEY=eyJ...
   SUPABASE_JWT_SECRET=your-jwt-secret
   DEV_AUTH_ENABLED=false
   ```

3. Run migration: `pnpm db:migrate`
4. Start stack: `pnpm dev`
5. Verify:
   - `/portfolio` signed out → redirects to `/sign-in?redirectedFrom=/portfolio`
   - Sign up / sign in → lands on `/portfolio`
   - Refresh `/portfolio` → still signed in
   - Network tab: API calls include `Authorization: Bearer <token>`
   - `curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/v1/me` → 200
   - `/sign-out` → home, nav shows Sign in

## How to test production preview

1. Push branch; deploy Vercel preview + Railway preview (or point preview web at staging API).
2. Add preview URL to Supabase redirect URLs.
3. Set all env vars on Vercel preview and Railway.
4. Run acceptance tests from `docs/SUPABASE_AUTH_AUDIT.md`.

## Build / test results

| Command | Result |
|---------|--------|
| `pnpm --filter @tcgscan/web build` | Pass |
| `pnpm typecheck` | Pass |
| `uv run pytest` (apps/api) | 57 passed |
| `pnpm lint` | API has pre-existing ruff format drift in 4 untouched files (`alembic/env.py`, etc.) |

## Remaining risks

1. **Supabase env not set** — middleware allows public routes through; protected routes redirect to sign-in but sign-in/sign-up throw if env missing.
2. **Email confirmation** — if enabled in Supabase, sign-up shows “check your email” instead of immediate session.
3. **Existing users** — email linking on first Supabase login attaches `supabase_user_id` to existing row.
4. **Edge middleware warning** — Supabase client uses Node APIs in Edge middleware (build warning only; runtime OK on Vercel).
5. **Production env cutover** — run Alembic `0009` on Railway before deploy.
6. **Stripe** — customer mapping uses local `users.id`; metadata includes `supabase_user_id`.

## Next steps (manual)

1. Configure Supabase project + env vars on Vercel and Railway.
2. Run `pnpm db:migrate` against Railway Postgres.
3. Deploy `supabase-auth-migration` branch to preview.
4. Complete acceptance checklist in `docs/SUPABASE_AUTH_AUDIT.md`.
5. Merge to main only after preview tests pass.
