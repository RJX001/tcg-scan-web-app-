"use client";

import { useAuth } from "@clerk/nextjs";

export function DevBanner() {
  const { isSignedIn } = useAuth();
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "";
  const isLocalApi =
    apiUrl.includes("localhost") || apiUrl.includes("127.0.0.1");

  if (!isLocalApi || isSignedIn || process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY) {
    return null;
  }

  return (
    <div className="border-b border-amber-200 bg-amber-50 px-4 py-2 text-center text-xs text-amber-900">
      Local demo mode — API calls use <strong>dev-user</strong> until you sign in with Clerk.
    </div>
  );
}
