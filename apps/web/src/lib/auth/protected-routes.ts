/** Routes that require a Supabase session. Everything else is public and
 * must never be blocked by middleware. */
export const PROTECTED_PREFIXES = [
  "/portfolio",
  "/watchlist",
  "/alerts",
  "/account",
  "/admin",
  "/collection",
] as const;

export function isProtectedPath(pathname: string): boolean {
  return PROTECTED_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
}
