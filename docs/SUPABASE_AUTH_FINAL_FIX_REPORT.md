# Supabase Auth Final Fix Report

> **Historical.** Cookie/session fixes from this report are in the tree. Prefer current `apps/web` middleware + `AGENTS.md` for behaviour.

Date: 2026-06-15  
Scope: Auth only — no Stripe, API features, styling, or unrelated pages.

## Executive summary

The live auth flow was broken because Supabase session cookies were never reliably persisted in middleware. The root cause was recreating `NextResponse` inside the Supabase `setAll` cookie handler, which dropped previously written `sb-*` cookies (including chunked auth cookies). That led to:

- No `sb-` cookies in the browser (`document.cookie.includes("sb-") === false`)
- Protected routes like `/portfolio` sometimes loading without a real session
- Nav showing **Account + Sign out** when no valid `access_token` existed
- Sign-in appearing to succeed but middleware not seeing the session on the next navigation

This fix makes session persistence, route protection, nav state, and API token injection all derive from the same truth: a Supabase session with a real `access_token`.

---

## Root cause

### 1. Middleware cookie handler dropped auth cookies (critical)

**File:** `apps/web/src/lib/supabase/middleware.ts` (before fix)

The Supabase SSR client's `setAll` callback was creating a **new** `NextResponse.next({ request })` on every cookie write. Supabase auth often sets multiple cookies (access token, refresh token, chunked values). Each `setAll` call replaced the previous response, so only the last cookie survived — or none at all reached the browser.

**Symptom:** After sign-in, `sb-*` cookies were missing; middleware `getUser()` returned null; nav/API had inconsistent state.

### 2. Redirect responses did not copy Supabase cookies

When middleware redirected unauthenticated users to `/sign-in`, the redirect response was a fresh `NextResponse.redirect()` without copying cookies from the session-refresh response. Refreshed tokens set during the same request could be lost.

### 3. Nav and sign-in used weak session signals

Nav could show signed-in UI without verifying `session?.access_token`. Sign-in used client-side `router.push()` which did not force a full navigation, so middleware sometimes ran before cookies were visible.

### 4. Server client silently swallowed cookie write errors

**File:** `apps/web/src/lib/supabase/server.ts` (before fix)

Cookie writes in Server Components were wrapped in try/catch and ignored. Failures to persist session cookies were invisible.

### 5. API bridge did not clear token on sign-out

**File:** `apps/web/src/components/auth-bridge.tsx` (before fix)

`SIGNED_OUT` did not always reset the SDK auth token getter, so stale Bearer tokens could be sent to `/v1/me`.

---

## What was fixed

| Area | Fix |
|------|-----|
| Browser client | Singleton `createBrowserClient` via `@supabase/ssr`; env vars only; no Clerk |
| Server client | `createServerClient` with Next `cookies()`; cookie writes no longer silently ignored |
| Middleware helper | `setAll` writes to the **existing** response only; never recreates `NextResponse` |
| Root middleware | Single response object; `getUser()` for protection; `copyResponseCookies` on redirects |
| Sign-in | Show `error.message`; validate `session?.access_token`; `window.location.assign(redirectedFrom)` |
| Sign-up | Show errors; email-confirm message; full navigation when session exists immediately |
| Auth nav | `getSession()` + `access_token`; `onAuthStateChange` for SIGNED_IN/TOKEN_REFRESHED/USER_UPDATED/SIGNED_OUT |
| Sign-out | Client `signOut()` + full nav to `/`; server `/sign-out` route clears cookies on redirect response |
| API bridge | Token from `getSession()`; updates on auth events; clears on `SIGNED_OUT` |
| Debug | Temporary `/debug-auth` page for session/cookie diagnostics |

---

## Files changed

```
apps/web/src/lib/supabase/browser.ts
apps/web/src/lib/supabase/server.ts
apps/web/src/lib/supabase/middleware.ts
apps/web/src/middleware.ts
apps/web/src/app/sign-in/sign-in-form.tsx
apps/web/src/app/sign-up/page.tsx
apps/web/src/app/sign-out/route.ts
apps/web/src/components/auth-nav.tsx
apps/web/src/components/auth-bridge.tsx
apps/web/src/app/debug-auth/page.tsx          (new)
docs/SUPABASE_AUTH_FINAL_FIX_REPORT.md        (this file)
```

---

## How middleware now protects `/portfolio`

1. Root `apps/web/src/middleware.ts` runs for all non-static routes (matcher includes `/portfolio`).
2. Creates **one** `NextResponse.next({ request })`.
3. Calls `updateSession(request, response)` which:
   - Builds `createServerClient` with request cookies read + response cookies written via `setAll` (no response recreation).
   - Calls `supabase.auth.getUser()` (server-validated user, not client-only `getSession()`).
4. If path starts with `/portfolio`, `/watchlist`, `/alerts`, `/account`, or `/admin` and `user` is null:
   - Redirect to `/sign-in?redirectedFrom=<pathname>`.
   - Copy all Supabase cookies from the session response onto the redirect via `copyResponseCookies()`.

---

## How sign-in stores and validates session

1. `signInWithPassword({ email, password })` via browser client.
2. On error → display `error.message` in a visible alert; **no redirect**.
3. On success → `getSession()` and require `session?.access_token`.
4. If token missing → show: *"Signed in but no session was created. Please refresh and try again."*
5. If token exists → `window.location.assign(redirectedFrom ?? "/portfolio")` so middleware receives fresh cookies on a full page load.

---

## How nav decides signed-in state

1. On mount: `supabase.auth.getSession()` → `hasSession = Boolean(session?.access_token)`.
2. Subscribes to `onAuthStateChange` for `SIGNED_IN`, `TOKEN_REFRESHED`, `USER_UPDATED`, `SIGNED_OUT`.
3. **Signed in** (access token present): Account link + Sign out button.
4. **Signed out**: Sign in link only.
5. Loading placeholder until first `getSession()` resolves (avoids flashing wrong state).

---

## How sign-out clears session

**Client (auth nav):**

1. `supabase.auth.signOut()`
2. Set local nav state to signed out
3. `window.location.assign("/")`

**Server (`GET /sign-out`):**

1. `createServerClient` with cookies read from request, written onto redirect response
2. `supabase.auth.signOut()` clears session cookies on the response
3. Redirect to `/`

After sign-out: nav shows Sign in; `/portfolio` redirects to `/sign-in?redirectedFrom=%2Fportfolio`; user is not auto-logged back in.

---

## How `/v1/me` gets the Authorization header

`SupabaseAuthBridge` (mounted in app layout):

1. On mount: `getSession()` → `setAuthTokenGetter(() => session.access_token)`.
2. On auth state change: update token from new session; on `SIGNED_OUT` set getter to `null`.
3. `@tcgscan/sdk-ts` attaches `Authorization: Bearer <token>` on every API request when a token is set.

Frontend calls to `/v1/me` include the Supabase access token when the user is logged in.

---

## Protected routes

| Route | Unauthenticated behaviour |
|-------|---------------------------|
| `/portfolio` | Redirect → `/sign-in?redirectedFrom=%2Fportfolio` |
| `/watchlist` | Redirect → `/sign-in?redirectedFrom=%2Fwatchlist` |
| `/alerts` | Redirect → `/sign-in?redirectedFrom=%2Falerts` |
| `/account` | Redirect → `/sign-in?redirectedFrom=%2Faccount` |
| `/admin` | Redirect → `/sign-in?redirectedFrom=%2Fadmin` |

---

## Debug page

Temporary route: `/debug-auth`

Displays (no token values):

- `hasSession`
- `hasAccessToken`
- `user email`
- `cookieHasSbPrefix`
- `localStorageSupabaseKeys` count

Remove before production GA.

---

## Commands run and results

```bash
pnpm --filter @tcgscan/web build
# ✓ Compiled successfully; middleware 90.3 kB; /debug-auth route present

pnpm typecheck
# ✓ 9/9 tasks successful

uv run pytest apps/api -q
# 58 passed, 2 warnings (test JWT key length only)
```

---

## Commit

```
fix: stabilise Supabase auth session handling
```

Pushed to `main`.

---

## Post-deploy verification checklist

1. Sign in with valid credentials → browser has `sb-*` cookies; `/debug-auth` shows `hasAccessToken: true`.
2. Visit `/portfolio` logged out → redirect to `/sign-in?redirectedFrom=%2Fportfolio`.
3. Sign in with wrong password → Supabase error message visible (e.g. invalid credentials).
4. Nav logged out → **Sign in** only; logged in → **Account + Sign out**.
5. Sign out → land on `/`; `/portfolio` redirects to sign-in; nav shows Sign in.
6. Network tab: API calls include `Authorization: Bearer …`; `/v1/me` returns 200 when logged in.
