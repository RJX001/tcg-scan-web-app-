# Clerk Removal and Supabase Auth Report

Branch: `supabase-auth-migration`  
Date: 2026-06-15

## Clerk fully removed

Clerk is no longer used anywhere in active application code. Supabase Auth is the sole identity provider.

### Frontend

- Removed `@clerk/nextjs` from `apps/web/package.json`
- Updated `pnpm-lock.yaml` (no `@clerk/*` packages)
- No active imports of `@clerk/nextjs`, `ClerkProvider`, `clerkMiddleware`, etc.
- Removed Clerk domains from `vercel.json` Content-Security-Policy
- Removed `/.clerk/` from `apps/web/.gitignore`

### Backend

- Removed `clerk-backend-api` from `apps/api/pyproject.toml`
- Updated `uv.lock` (no `clerk-backend-api`)
- Deleted `_verify_clerk_bearer` and all Clerk JWT fallback logic from `tcgscan_api/middleware/auth.py`
- Removed `CLERK_SECRET_KEY` and `CLERK_AUTHORIZED_PARTIES` from `tcgscan_api/config.py`
- Production startup requires `SUPABASE_JWT_SECRET` or `SUPABASE_JWKS_URL` (unchanged from prior migration)

### Environment variables

- Removed all Clerk env vars from `.env.example`
- Added comment: `# Removed: Clerk auth no longer used`
- Vercel/Railway: delete any remaining `CLERK_*` and `NEXT_PUBLIC_CLERK_*` vars from dashboards

### Database: `users.clerk_id`

- **Dropped** from SQLAlchemy model (`tcgscan_api/db/models.py`)
- **Dropped** from database via Alembic migration `0009_drop_clerk_id`
- Historical references remain only in old migrations `0002` and `0008` (not edited)

### Active code identity field

All auth paths now use `supabase_user_id`:

- `AuthUser.supabase_user_id` (required)
- `UsersRepo.get_or_create(supabase_user_id=...)`
- `AccountOut.supabase_user_id` (API + SDK)
- Stripe customer metadata: `supabase_user_id` + `user_id`
- Dev bypass: `X-Dev-User-Id` maps to `supabase_user_id`

### Tests

- All fixtures updated from `clerk_id` to `supabase_user_id`
- Added `test_supabase_bearer_token_accepted` — verifies HS256 JWT with `SUPABASE_JWT_SECRET`
- Dev-header tests unchanged in behaviour; assert `supabase_user_id`

## Final verification commands

```powershell
git branch --show-current
git log -1 --oneline

pnpm --filter @tcgscan/web build
pnpm typecheck

cd apps/api
uv run pytest -q
```

Search for remaining Clerk references (excluding docs and old Alembic history):

```powershell
rg -n -S -i "clerk|@clerk|CLERK_|clerk_id|_verify_clerk_bearer" apps packages pyproject.toml package.json pnpm-lock.yaml uv.lock .env.example vercel.json --glob "!**/node_modules/**" --glob "!**/.next/**" --glob "!**/.git/**" --glob "!**/dist/**" --glob "!**/build/**" --glob "!docs/**"
```

Expected: matches only in `apps/api/alembic/versions/0002_*`, `0008_*`, `0009_*` (historical migration text).

## Remaining manual steps

1. Run `pnpm db:migrate` on Railway to apply `0009_drop_clerk_id`
2. Remove Clerk env vars from Vercel and Railway dashboards
3. Remove Clerk project or leave dormant (no code dependency)
4. Deploy branch preview and run acceptance tests from `docs/SUPABASE_AUTH_AUDIT.md`
5. Do not merge to `main` until preview passes
