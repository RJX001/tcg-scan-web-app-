# apps/web — AGENTS.md

Next.js 15 App Router. Server Components by default. Mobile-first (`sm` breakpoint).

Card pages: ISR `revalidate: 900`. Use `@tcgscan/sdk-ts` for API calls (no marketplace HTTP from the browser).

Auth: Supabase SSR (`@supabase/ssr`). Protected prefixes: portfolio, watchlist, alerts, account, admin, collection. `SupabaseAuthBridge` injects the access token into sdk-ts.
