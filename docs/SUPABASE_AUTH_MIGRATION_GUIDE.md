# TCG Chart — Supabase Auth Migration Guide

> **Historical runbook.** Supabase Auth is live; Clerk is removed.
> Do not re-execute these phases. Prefer `docs/CLERK_REMOVAL_AND_SUPABASE_AUTH_REPORT.md` and current `AGENTS.md`.

## Decision

We are stopping the Clerk auth integration and migrating to **Supabase Auth**.

Reason: the production Clerk setup repeatedly behaved unreliably in this project:

- Account portal blank/redirect issues.
- Embedded `<SignIn />` rendered as an empty/zero-size component.
- `needs_client_trust` issue.
- Client session existed in `window.Clerk`, and cookies existed, but protected routes and the nav still failed.
- `/portfolio` still redirected back to the homepage even after multiple Clerk fixes.

This is now considered a launch-risk. Auth needs to be stable and boring.

## Migration Principle

Do **not** migrate the full database yet.

For now:

- Supabase = Auth provider only.
- Railway PostgreSQL = keep existing application database.
- Railway FastAPI backend = stays as the API.
- Vercel Next.js frontend = stays as the frontend.
- Stripe = keep current Stripe setup, but remap user identity from Clerk ID to Supabase user ID.

The target architecture:

```txt
Supabase Auth login/signup
↓
Frontend receives Supabase session/access_token
↓
Frontend sends Authorization: Bearer <supabase_access_token> to FastAPI
↓
FastAPI verifies Supabase JWT
↓
FastAPI maps Supabase user_id to local users table
↓
Portfolio/account/pro features work
```

---

# Phase 0 — Branch and Audit

Create a branch first:

```bash
git checkout -b supabase-auth-migration
```

Create this file in the repo:

```txt
docs/SUPABASE_AUTH_MIGRATION_GUIDE.md
```

Then audit the repo for all Clerk usage.

Search for:

```txt
@clerk/nextjs
ClerkProvider
UserButton
SignedIn
SignedOut
SignIn
SignUp
SignInButton
useUser
useAuth
auth()
clerkMiddleware
AuthBridge
CLERK_SECRET_KEY
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
NEXT_PUBLIC_CLERK_JS_URL
CLERK_AUTHORIZED_PARTIES
clerk_id
_verify_clerk_bearer
```

Create a checklist in `docs/SUPABASE_AUTH_AUDIT.md` listing every file found and what needs changing.

Do not delete Clerk until the replacement is implemented.

---

# Phase 1 — Supabase Project Setup

Create a Supabase project in the Supabase dashboard.

Configure Auth:

1. Enable Email + Password.
2. Enable Email confirmations only if desired for production.
3. Configure Site URL:

```txt
https://www.cardchart.co.uk
```

4. Configure redirect URLs:

```txt
https://www.cardchart.co.uk/auth/callback
https://cardchart.co.uk/auth/callback
http://localhost:3000/auth/callback
http://localhost:3001/auth/callback
```

5. Optional: enable Google OAuth later after email/password works.

Required environment variables:

Frontend/Vercel:

```txt
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_API_URL=https://tcg-scan-web-app-production.up.railway.app
```

Backend/Railway:

```txt
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_JWT_SECRET=
SUPABASE_JWKS_URL=https://YOUR_PROJECT_REF.supabase.co/auth/v1/.well-known/jwks.json
```

Optional backend admin variable, only if needed for admin tasks:

```txt
SUPABASE_SERVICE_ROLE_KEY=
```

Never expose `SUPABASE_SERVICE_ROLE_KEY` to the frontend.

---

# Phase 2 — Frontend Package Changes

In the web app workspace, install Supabase packages:

```bash
pnpm --filter @tcgscan/web add @supabase/supabase-js @supabase/ssr
```

Remove Clerk once migration is complete and tested:

```bash
pnpm --filter @tcgscan/web remove @clerk/nextjs
```

Do not remove Clerk at the start. Remove it only after all Supabase auth flows pass.

---

# Phase 3 — Frontend Supabase Clients

Create:

```txt
apps/web/src/lib/supabase/client.ts
apps/web/src/lib/supabase/server.ts
apps/web/src/lib/supabase/middleware.ts
```

## `apps/web/src/lib/supabase/client.ts`

```ts
import { createBrowserClient } from "@supabase/ssr";

export function createClient() {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!supabaseUrl || !supabaseAnonKey) {
    throw new Error("Missing Supabase frontend environment variables");
  }

  return createBrowserClient(supabaseUrl, supabaseAnonKey);
}
```

## `apps/web/src/lib/supabase/server.ts`

Use the current Next.js App Router cookie API. For Next.js 15, `cookies()` may be async. Implement according to the installed Next.js version.

Expected behaviour:

- Create a server Supabase client.
- Read cookies from `next/headers`.
- Allow Server Components and Route Handlers to call `supabase.auth.getUser()`.
- Never trust `getSession()` server-side for authorization; use `getUser()` where possible.

## `apps/web/src/lib/supabase/middleware.ts`

Implement Supabase middleware to refresh the auth session and expose cookies correctly.

Expected behaviour:

- Create Supabase server client inside middleware.
- Call `supabase.auth.getUser()`.
- Return the updated `NextResponse` with any refreshed cookies.

---

# Phase 4 — Replace Middleware Protection

Current Clerk middleware must be removed.

Replace `apps/web/src/middleware.ts` with Supabase-based route protection.

Protected routes:

```txt
/portfolio
/watchlist
/alerts
/account
/admin
```

Expected behaviour:

- If the route is public, allow through.
- If the route is protected and user is authenticated, allow through.
- If the route is protected and user is not authenticated, redirect to:

```txt
/sign-in?redirectedFrom=<original_path>
```

Implementation shape:

```ts
import { type NextRequest, NextResponse } from "next/server";
import { createServerClient } from "@supabase/ssr";

const protectedPrefixes = ["/portfolio", "/watchlist", "/alerts", "/account", "/admin"];

export async function middleware(request: NextRequest) {
  let response = NextResponse.next({ request });

  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!supabaseUrl || !supabaseAnonKey) {
    return response;
  }

  const supabase = createServerClient(supabaseUrl, supabaseAnonKey, {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(cookiesToSet) {
        cookiesToSet.forEach(({ name, value, options }) => {
          request.cookies.set(name, value);
          response.cookies.set(name, value, options);
        });
      },
    },
  });

  const {
    data: { user },
  } = await supabase.auth.getUser();

  const pathname = request.nextUrl.pathname;
  const isProtected = protectedPrefixes.some((prefix) => pathname.startsWith(prefix));

  if (isProtected && !user) {
    const redirectUrl = request.nextUrl.clone();
    redirectUrl.pathname = "/sign-in";
    redirectUrl.searchParams.set("redirectedFrom", pathname);
    return NextResponse.redirect(redirectUrl);
  }

  return response;
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
```

Cursor should adjust this for the exact project structure and TypeScript rules.

---

# Phase 5 — Remove Clerk Provider From Layout

In `apps/web/src/app/layout.tsx`:

Remove:

```txt
ClerkProvider
UserButton
SignedIn
SignedOut
SignInButton
Show from @clerk/nextjs
auth() from @clerk/nextjs/server
```

Replace with a Supabase-aware client nav.

Create:

```txt
apps/web/src/components/auth-nav.tsx
```

Use a simple stable version first:

```tsx
"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";

export function AuthNavDesktop() {
  const [isSignedIn, setIsSignedIn] = useState<boolean | null>(null);
  const supabase = createClient();

  useEffect(() => {
    let mounted = true;

    supabase.auth.getUser().then(({ data }) => {
      if (mounted) setIsSignedIn(Boolean(data.user));
    });

    const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {
      setIsSignedIn(Boolean(session?.user));
    });

    return () => {
      mounted = false;
      listener.subscription.unsubscribe();
    };
  }, [supabase]);

  if (isSignedIn) {
    return (
      <a
        href="/account"
        className="rounded-full bg-blue-700 px-4 py-1.5 text-sm font-semibold text-white hover:bg-blue-800"
      >
        Account
      </a>
    );
  }

  return (
    <Link
      href="/sign-in"
      className="rounded-full bg-blue-700 px-4 py-1.5 text-sm font-semibold text-white hover:bg-blue-800"
    >
      Sign in
    </Link>
  );
}

export function AuthNavMobile() {
  const [isSignedIn, setIsSignedIn] = useState<boolean | null>(null);
  const supabase = createClient();

  useEffect(() => {
    let mounted = true;

    supabase.auth.getUser().then(({ data }) => {
      if (mounted) setIsSignedIn(Boolean(data.user));
    });

    const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {
      setIsSignedIn(Boolean(session?.user));
    });

    return () => {
      mounted = false;
      listener.subscription.unsubscribe();
    };
  }, [supabase]);

  if (isSignedIn) {
    return (
      <a href="/account" className="text-sm font-semibold text-blue-700">
        Account
      </a>
    );
  }

  return (
    <Link href="/sign-in" className="text-sm font-semibold text-blue-700">
      Sign in
    </Link>
  );
}
```

Then use `<AuthNavDesktop />` and `<AuthNavMobile />` inside `layout.tsx`.

---

# Phase 6 — Sign In, Sign Up, Callback, Sign Out

Replace the Clerk sign-in/sign-up pages.

Remove these Clerk pages:

```txt
apps/web/src/app/sign-in/[[...sign-in]]/page.tsx
apps/web/src/app/sign-up/[[...sign-up]]/page.tsx
```

Replace with normal pages:

```txt
apps/web/src/app/sign-in/page.tsx
apps/web/src/app/sign-up/page.tsx
apps/web/src/app/auth/callback/route.ts
apps/web/src/app/sign-out/route.ts
```

## Sign in page requirements

- Email input.
- Password input.
- Submit button.
- Link to sign up.
- Optional Google button later.
- On success, redirect to `redirectedFrom` query param or `/portfolio`.
- Show readable error messages.

Use:

```ts
supabase.auth.signInWithPassword({ email, password })
```

## Sign up page requirements

- Email input.
- Password input.
- Submit button.
- Link to sign in.
- On success, either show "check your email" or redirect to `/portfolio` depending on Supabase email confirmation settings.

Use:

```ts
supabase.auth.signUp({ email, password })
```

## Auth callback route

Required for OAuth and email confirmation flows.

Use:

```ts
supabase.auth.exchangeCodeForSession(code)
```

Then redirect to `next` or `/portfolio`.

## Sign out route

Use:

```ts
supabase.auth.signOut()
```

Then redirect to `/`.

---

# Phase 7 — Replace AuthBridge

Current app likely has an `AuthBridge` that gets a Clerk token and passes it to the SDK/API client.

Replace it with `SupabaseAuthBridge`.

Expected behaviour:

- On load, call `supabase.auth.getSession()`.
- If access token exists, set API client Authorization header:

```txt
Authorization: Bearer <supabase_access_token>
```

- Listen to `onAuthStateChange`.
- Update API token when user signs in, signs out, or token refreshes.
- Clear API token on sign out.

Search for the current SDK token setter before implementing. Reuse the existing API client pattern.

---

# Phase 8 — Backend Supabase JWT Verification

Replace Clerk verification in FastAPI.

Current likely file:

```txt
apps/api/tcgscan_api/middleware/auth.py
```

Remove Clerk-specific logic:

```txt
_verify_clerk_bearer
clerk_id
CLERK_SECRET_KEY
CLERK_AUTHORIZED_PARTIES
clerk_backend_api
```

Replace with Supabase JWT verification.

Auth middleware should:

1. Read `Authorization: Bearer <token>`.
2. Verify the Supabase JWT.
3. Extract:

```txt
sub = Supabase user UUID
audios/aud = authenticated
email = email claim if present
role = authenticated
exp = expiry
iss = Supabase issuer
```

4. Find or create local user row by Supabase user ID.
5. Attach user to request state.
6. Return 401 if token missing on protected endpoints.
7. Allow public endpoints where required.

## Verification strategy

Cursor should implement robust verification using one of these approaches:

### Preferred

Use Supabase JWKS if project uses asymmetric signing keys:

```txt
SUPABASE_JWKS_URL=https://YOUR_PROJECT_REF.supabase.co/auth/v1/.well-known/jwks.json
```

Cache JWKS keys.

### Fallback

Use `SUPABASE_JWT_SECRET` for HS256 projects.

Validate:

```txt
issuer: https://YOUR_PROJECT_REF.supabase.co/auth/v1
audience: authenticated
expiration: required
sub: required
```

Suggested Python dependencies if missing:

```bash
uv add pyjwt cryptography
```

or, if using project package management:

```bash
uv add --package tcgscan-api pyjwt cryptography
```

Cursor must check the repo's dependency setup before adding packages.

---

# Phase 9 — User Table Mapping

Do not delete existing user data.

Add a nullable Supabase user ID column to the local users table.

Use Alembic only. Never manually alter production DB.

Possible migration:

```txt
users.supabase_user_id UUID UNIQUE NULL
```

Keep existing `clerk_id` column temporarily for rollback.

User mapping rules:

- On authenticated request, read `sub` from Supabase JWT.
- Find user by `supabase_user_id`.
- If not found, create user with:

```txt
supabase_user_id = token.sub
email = token.email if available
tier = free
role = user
```

- If old Clerk users exist and email matches, optionally link the existing user by email instead of creating a duplicate.

Do not remove `clerk_id` until migration is stable.

---

# Phase 10 — Stripe Mapping

Stripe should map to local user records, not directly to Clerk or Supabase.

Keep:

```txt
stripe_customer_id
stripe_subscription_id
subscription_status
tier
```

Update any code that used Clerk ID to identify Stripe customer.

New rule:

```txt
Supabase user ID → local users row → Stripe customer/subscription
```

Stripe webhook logic should update the local user row as before.

---

# Phase 11 — Environment Cleanup

After Supabase is fully working, remove Clerk env vars from Vercel and Railway:

```txt
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
NEXT_PUBLIC_CLERK_SIGN_IN_URL
NEXT_PUBLIC_CLERK_SIGN_UP_URL
NEXT_PUBLIC_CLERK_SIGN_IN_FALLBACK_REDIRECT_URL
NEXT_PUBLIC_CLERK_SIGN_UP_FALLBACK_REDIRECT_URL
NEXT_PUBLIC_CLERK_JS_URL
CLERK_SECRET_KEY
CLERK_AUTHORIZED_PARTIES
```

Do not remove them until Supabase auth is verified in production.

---

# Phase 12 — Acceptance Tests

Run these before merging to main.

## Local tests

1. Homepage loads signed out.
2. `/portfolio` signed out redirects to `/sign-in?redirectedFrom=/portfolio`.
3. Sign up creates a Supabase user.
4. Sign in redirects to `/portfolio`.
5. Refresh `/portfolio`; user remains signed in.
6. API call to `/v1/me` returns 200 when signed in.
7. API call to `/v1/me` returns 401 when signed out.
8. Sign out clears session.
9. Refresh homepage after sign out; nav shows Sign in.
10. No Clerk JS files load in Network tab.

## Production preview tests

Deploy branch to Vercel preview.

Test:

```txt
https://<preview-url>.vercel.app
```

Supabase redirect URLs must include the preview URL during testing.

## Production tests

After merge:

1. `https://www.cardchart.co.uk` loads.
2. Sign up works.
3. Sign in works.
4. `/portfolio` works.
5. `/v1/me` works with authenticated token.
6. Sign out works.
7. No Clerk scripts or Clerk cookies remain.

---

# Phase 13 — Rollback Plan

Do not delete the Clerk branch/config immediately.

Rollback options:

1. Revert the Supabase migration commit.
2. Restore Clerk env vars.
3. Redeploy previous Vercel production build.
4. Redeploy Railway previous backend build.

Keep `clerk_id` in the database until Supabase has been stable for at least one full production testing cycle.

---

# Cursor Implementation Order

Do this in order:

1. Create `supabase-auth-migration` branch.
2. Add this markdown guide.
3. Audit Clerk usage into `docs/SUPABASE_AUTH_AUDIT.md`.
4. Install Supabase packages in web app.
5. Add Supabase frontend clients.
6. Replace middleware.
7. Replace layout provider/nav.
8. Replace sign-in/sign-up pages.
9. Add auth callback and sign-out route.
10. Replace `AuthBridge` with `SupabaseAuthBridge`.
11. Add backend Supabase JWT verification.
12. Add Alembic migration for `users.supabase_user_id` if needed.
13. Update `/v1/me` to return Supabase-authenticated user.
14. Run typecheck/build/tests.
15. Deploy Vercel preview.
16. Test preview thoroughly.
17. Only then merge to main.

---

# Definition of Done

The migration is complete only when:

- Clerk is no longer imported anywhere in the frontend.
- Clerk is no longer used in backend auth middleware.
- Supabase sign-up works.
- Supabase sign-in works.
- `/portfolio` stays open after refresh.
- `/v1/me` returns the correct user when signed in.
- `/v1/me` returns 401 when signed out.
- Stripe user mapping still works through the local user table.
- Vercel production deploy is green.
- Railway backend deploy is green.
- No Clerk env vars are required for the app to run.
