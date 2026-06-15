"use client";

import { useEffect, useState } from "react";

import { createClient } from "@/lib/supabase/browser";

export function DevBanner() {
  const [isSignedIn, setIsSignedIn] = useState<boolean | null>(null);
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "";
  const isLocalApi = apiUrl.includes("localhost") || apiUrl.includes("127.0.0.1");

  useEffect(() => {
    let mounted = true;
    try {
      const supabase = createClient();
      supabase.auth.getUser().then(({ data }) => {
        if (mounted) setIsSignedIn(Boolean(data.user));
      });
    } catch {
      if (mounted) setIsSignedIn(false);
    }
    return () => {
      mounted = false;
    };
  }, []);

  if (!isLocalApi || isSignedIn || process.env.NEXT_PUBLIC_SUPABASE_URL) {
    return null;
  }

  return (
    <div className="border-b border-amber-200 bg-amber-50 px-4 py-2 text-center text-xs text-amber-900">
      Local demo mode — API calls use <strong>dev-user</strong> until you sign in with Supabase.
    </div>
  );
}
