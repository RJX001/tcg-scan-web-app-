export function DevBanner() {
  if (process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY) return null;
  return (
    <div className="border-b border-amber-200 bg-amber-50 px-4 py-2 text-center text-xs text-amber-900">
      Local demo mode — signed in as <strong>dev-user</strong> (Pro). Configure Clerk keys for real auth.
    </div>
  );
}
