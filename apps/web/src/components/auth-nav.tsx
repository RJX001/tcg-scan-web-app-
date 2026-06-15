"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { createClient } from "@/lib/supabase/browser";

function useAuthSignedIn() {
  const [isSignedIn, setIsSignedIn] = useState<boolean | null>(null);

  useEffect(() => {
    let mounted = true;
    const supabase = createClient();

    supabase.auth.getUser().then(({ data }) => {
      if (mounted) setIsSignedIn(Boolean(data.user));
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setIsSignedIn(Boolean(session?.user));
    });

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, []);

  return isSignedIn;
}

export function AuthNavDesktop() {
  const isSignedIn = useAuthSignedIn();

  if (isSignedIn) {
    return (
      <div className="flex items-center gap-3">
        <Link
          href="/portfolio"
          className="rounded-full bg-blue-700 px-4 py-1.5 text-sm font-semibold text-white hover:bg-blue-800"
        >
          Account
        </Link>
        <Link href="/sign-out" className="text-sm font-medium text-zinc-600 hover:text-zinc-900">
          Sign out
        </Link>
      </div>
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
  const isSignedIn = useAuthSignedIn();

  if (isSignedIn) {
    return (
      <div className="flex items-center gap-3">
        <Link href="/portfolio" className="text-sm font-semibold text-blue-700">
          Account
        </Link>
        <Link href="/sign-out" className="text-sm font-medium text-zinc-600">
          Out
        </Link>
      </div>
    );
  }

  return (
    <Link href="/sign-in" className="text-sm font-semibold text-blue-700">
      Sign in
    </Link>
  );
}
