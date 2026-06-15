"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { createClient } from "@/lib/supabase/browser";

function useHasSession() {
  const [hasSession, setHasSession] = useState<boolean | null>(null);

  useEffect(() => {
    let mounted = true;
    const supabase = createClient();

    void supabase.auth.getSession().then(({ data: { session } }) => {
      if (mounted) setHasSession(Boolean(session?.access_token));
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setHasSession(Boolean(session?.access_token));
    });

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, []);

  return hasSession;
}

export function AuthNavDesktop() {
  const hasSession = useHasSession();

  if (hasSession === null) {
    return <span className="inline-block h-8 w-28" aria-hidden />;
  }

  if (hasSession) {
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
  const hasSession = useHasSession();

  if (hasSession === null) {
    return <span className="inline-block h-4 w-16" aria-hidden />;
  }

  if (hasSession) {
    return (
      <div className="flex items-center gap-3">
        <Link href="/portfolio" className="text-sm font-semibold text-blue-700">
          Account
        </Link>
        <Link href="/sign-out" className="text-sm font-medium text-zinc-600">
          Sign out
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
