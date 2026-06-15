# Supabase Auth Implementation Report

Branch: `supabase-auth-migration`  
Date: 2026-06-15

## Summary

Replaced Clerk with Supabase Auth for sign-in/sign-up, session management, route protection, and API Bearer token verification. Railway PostgreSQL remains the application database. Clerk code and env vars are retained as deprecated fallbacks until production verification.

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
| `tcgscan_api/middleware/auth.py` | Supabase JWT verify (JWKS + HS256); Clerk fallback |
| `tcgscan_api/config.py` | Supabase settings |
| `tcgscan_api/main.py` | Production requires Supabase JWT config |
| `tcgscan_api/db/models.py` | `supabase_user_id`; `clerk_id` nullable |
| `tcgscan_api/repositories/users.py` | `get_or_create_by_supabase` + email linking |
| `tcgscan_api/services/auth_ctx.py` | Resolve DB user by Supabase or Clerk id |
| `tcgscan_api/services/billing.py` | Stripe metadata includes `supabase_user_id` |
| `tcgscan_api/middleware/rate_limit.py` | Rate limit key uses Supabase or Clerk id |
| `alembic/versions/0008_supabase_user_id.py` | **New migration** |
| `pyproject.toml` | Added `pyjwt`, `cryptography` |
| Tests | Clear Supabase env in dev-auth tests |

### Shared

- `.env.example` — Supabase vars added; Clerk marked deprecated
- `packages/sdk-ts/src/index.ts` — Comment updated for Supabase bridge
- `pnpm-lock.yaml`, `uv.lock`

## Migration

**Alembic:** `0008_supabase_user_id`

```bash
pnpm db:migrate
# or: cd apps/api && uv run alembic upgrade head
```

Adds:

- `users.supabase_user_id` — `VARCHAR(36)`, nullable, unique, indexed
- `users.clerk_id` — altered to nullable

## Env vars — Vercel (frontend)

| Variable | Required | Notes |
|----------|----------|-------|
| `NEXT_PUBLIC_SUPABASE_URL` | Yes | From Supabase project settings |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Yes | Public anon key |
| `NEXT_PUBLIC_API_URL` | Yes | Railway API URL (unchanged) |
| `NEXT_PUBLIC_SITE_URL` | Yes | e.g. `https://www.cardchart.co.uk` |

Clerk vars can remain during rollout; they are no longer used by active frontend code.

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
3. **Existing Clerk users** — linked by matching email on first Supabase login; users with different emails get new rows.
4. **Clerk package still installed** — `@clerk/nextjs` in `package.json`; remove after production verification.
5. **Edge middleware warning** — Supabase client uses Node APIs in Edge middleware (build warning only; runtime OK on Vercel).
6. **Production env cutover** — must set Railway Supabase vars before removing Clerk vars; run Alembic on Railway DB.
7. **Stripe** — customer mapping unchanged; uses local `users.id`; metadata now includes `supabase_user_id`.

## Next steps (manual)

1. Configure Supabase project + env vars on Vercel and Railway.
2. Run `pnpm db:migrate` against Railway Postgres.
3. Deploy `supabase-auth-migration` branch to preview.
4. Complete acceptance checklist in `docs/SUPABASE_AUTH_AUDIT.md`.
5. Merge to main only after preview tests pass.
6. Remove Clerk package and env vars after one stable production cycle.
