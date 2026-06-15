import { type NextRequest, NextResponse } from "next/server";

import { copyResponseCookies, updateSession } from "@/lib/supabase/middleware";

const protectedPrefixes = ["/portfolio", "/watchlist", "/alerts", "/account", "/admin"];

export async function middleware(request: NextRequest) {
  const pathname = request.nextUrl.pathname;
  const isProtected = protectedPrefixes.some((prefix) => pathname.startsWith(prefix));

  let response = NextResponse.next({ request });
  const { supabaseResponse, user } = await updateSession(request, response);
  response = supabaseResponse;

  if (isProtected && !user) {
    const redirectUrl = request.nextUrl.clone();
    redirectUrl.pathname = "/sign-in";
    redirectUrl.searchParams.set("redirectedFrom", pathname);
    const redirectResponse = NextResponse.redirect(redirectUrl);
    return copyResponseCookies(response, redirectResponse);
  }

  return response;
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
