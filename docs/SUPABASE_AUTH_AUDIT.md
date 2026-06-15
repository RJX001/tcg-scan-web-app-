# Supabase Auth Migration — Clerk Audit

Audit date: 2026-06-15. Branch: `supabase-auth-migration`.

## Frontend (`apps/web`)

| File | Clerk usage | Replacement |
|------|-------------|-------------|
| `src/middleware.ts` | `clerkMiddleware`, `createRouteMatcher` | Supabase session refresh + protected route redirects |
| `src/app/layout.tsx` | `ClerkProvider`, `AuthBridge` | Remove provider; `SupabaseAuthBridge` |
| `src/components/auth-bridge.tsx` | `useAuth`, `getToken` → SDK | `SupabaseAuthBridge` with session access token |
| `src/components/auth-nav.tsx` | Static Account link (no Clerk) | Supabase-aware sign-in / account / sign-out |
| `src/components/dev-banner.tsx` | `useAuth`, `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Supabase `getUser()` + `NEXT_PUBLIC_SUPABASE_URL` |
| `src/app/sign-in/[[...sign-in]]/page.tsx` | `<SignIn />` | Delete; replace with `src/app/sign-in/page.tsx` |
| `src/app/sign-up/[[...sign-up]]/page.tsx` | `<SignUp />` | Delete; replace with `src/app/sign-up/page.tsx` |
| `package.json` | `@clerk/nextjs` dependency | Keep until E2E verified; remove in follow-up |
| `pnpm-lock.yaml` | `@clerk/nextjs` lock entry | Updates when Clerk removed |

## Backend (`apps/api`)

| File | Clerk usage | Replacement |
|------|-------------|-------------|
| `tcgscan_api/middleware/auth.py` | `_verify_clerk_bearer`, `clerk_backend_api`, `AuthUser.clerk_id` | Supabase JWT verify (JWKS/HS256); keep Clerk fallback |
| `tcgscan_api/config.py` | `CLERK_SECRET_KEY`, `CLERK_AUTHORIZED_PARTIES` | Add Supabase env vars; deprecate Clerk vars |
| `tcgscan_api/main.py` | Production startup requires `CLERK_SECRET_KEY` | Require Supabase JWT config in production |
| `tcgscan_api/services/auth_ctx.py` | `get_or_create(clerk_id=...)` | `get_or_create_by_supabase` when Supabase principal |
| `tcgscan_api/repositories/users.py` | Lookup/create by `clerk_id` only | Add `supabase_user_id` lookup + email linking |
| `tcgscan_api/db/models.py` | `User.clerk_id` NOT NULL unique | Add `supabase_user_id`; make `clerk_id` nullable |
| `tcgscan_api/services/billing.py` | Stripe metadata `clerk_id` | Add `supabase_user_id` to metadata; local user row unchanged |
| `tcgscan_api/middleware/rate_limit.py` | `_load_tier_for_clerk` | Key by `supabase_user_id` or `clerk_id` |
| `tcgscan_api/repositories/admin.py` | Search includes `clerk_id` | Keep; optionally add `supabase_user_id` later |
| `tcgscan_api/seed.py` | Seeds `clerk_id="dev-user"` | Unchanged for dev seed |
| `pyproject.toml` | `clerk-backend-api` dependency | Keep until Clerk fallback removed |
| `alembic/versions/0002_users_portfolio_alerts.py` | Original `clerk_id` column | Historical; new migration `0008` adds Supabase column |
| `tests/test_auth_production.py` | Clears `CLERK_SECRET_KEY` for dev bypass | Also clear Supabase JWT env vars |
| `tests/test_portfolio.py` | Clears `CLERK_SECRET_KEY` | Also clear Supabase JWT env vars |
| Other tests | `AuthUser(..., clerk_id=...)` | Unchanged; dev bypass still uses `clerk_id` |

## Shared / config

| File | Clerk usage | Replacement |
|------|-------------|-------------|
| `.env.example` | Clerk block | Add Supabase vars; mark Clerk deprecated |
| `packages/sdk-ts/src/index.ts` | Comment references Clerk `getToken` | Comment updated; `setAuthTokenGetter` unchanged |
| `CHANGELOG.md` | Documents Clerk integration | Add Supabase migration entry in follow-up |
| `AGENTS.md`, `CLAUDE.md`, `docs/TCG_Scan_Phase1.md` | Auth = Clerk | Docs update deferred (not in migration scope) |

## Env vars

### Deprecated (keep until production verified)

- `CLERK_SECRET_KEY`
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`
- `NEXT_PUBLIC_CLERK_SIGN_IN_URL`
- `NEXT_PUBLIC_CLERK_SIGN_UP_URL`
- `NEXT_PUBLIC_CLERK_SIGN_IN_FALLBACK_REDIRECT_URL`
- `NEXT_PUBLIC_CLERK_SIGN_UP_FALLBACK_REDIRECT_URL`
- `NEXT_PUBLIC_CLERK_JS_URL` (not in `.env.example` but may exist in Vercel)
- `CLERK_AUTHORIZED_PARTIES`

### New — frontend (Vercel)

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

### New — backend (Railway)

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_JWT_SECRET` (HS256 projects)
- `SUPABASE_JWKS_URL` (asymmetric signing; preferred when set)
- `SUPABASE_SERVICE_ROLE_KEY` (optional admin only)

## Database

| Table | Change |
|-------|--------|
| `users` | Add `supabase_user_id` UUID/text nullable unique indexed |
| `users` | `clerk_id` → nullable (keep for rollback) |

## Routes protected (unchanged)

- `/portfolio`
- `/watchlist`
- `/alerts`
- `/account`
- `/admin`

## Acceptance checklist

- [ ] Sign up / sign in via Supabase email+password
- [ ] Protected routes redirect to `/sign-in?redirectedFrom=...`
- [ ] `/v1/me` returns 200 with Bearer token
- [ ] `/v1/me` returns 401 without token
- [ ] Sign out clears session
- [ ] Stripe tier/role still from local `users` row
- [ ] No Clerk JS loaded in Network tab (after Clerk package removed)
