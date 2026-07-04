import { type NextRequest, NextResponse } from "next/server";

import { isProtectedPath } from "@/lib/auth/protected-routes";
import { copyResponseCookies, updateSession } from "@/lib/supabase/middleware";

/** Hard cap on the Supabase session check so middleware always fails fast
 * instead of hitting Vercel's MIDDLEWARE_INVOCATION_TIMEOUT. */
const SESSION_CHECK_TIMEOUT_MS = 5000;

const SESSION_CHECK_TIMED_OUT = Symbol("session-check-timed-out");

export async function middleware(request: NextRequest) {
  const pathname = request.nextUrl.pathname;

  // Public routes render immediately — no session refresh, no external calls.
  if (!isProtectedPath(pathname)) {
    return NextResponse.next();
  }

  let response = NextResponse.next({ request });

  try {
    const result = await Promise.race([
      updateSession(request, response),
      new Promise<typeof SESSION_CHECK_TIMED_OUT>((resolve) =>
        setTimeout(() => resolve(SESSION_CHECK_TIMED_OUT), SESSION_CHECK_TIMEOUT_MS),
      ),
    ]);

    if (result === SESSION_CHECK_TIMED_OUT) {
      // Fail open: let the page render. Protected pages verify the session
      // client-side and the API enforces auth on every request.
      return response;
    }

    response = result.supabaseResponse;

    if (!result.user) {
      const redirectUrl = request.nextUrl.clone();
      redirectUrl.pathname = "/sign-in";
      redirectUrl.searchParams.set("redirectedFrom", pathname);
      const redirectResponse = NextResponse.redirect(redirectUrl);
      return copyResponseCookies(response, redirectResponse);
    }
  } catch {
    // Session check failed unexpectedly — fail open rather than 504 the page.
    return response;
  }

  return response;
}

export const config = {
  // Middleware only runs on protected routes; public pages ( /, /shop, /cards,
  // /card/[slug], /sales, /indexes, /sign-in, /auth/callback, … ) never invoke it.
  matcher: [
    "/portfolio/:path*",
    "/watchlist/:path*",
    "/alerts/:path*",
    "/account/:path*",
    "/admin/:path*",
    "/collection/:path*",
  ],
};
