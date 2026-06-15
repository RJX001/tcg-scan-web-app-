"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { createClient } from "@/lib/supabase/browser";

const SESSION_EVENTS = new Set(["SIGNED_IN", "TOKEN_REFRESHED", "USER_UPDATED", "SIGNED_OUT"]);

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
    } = supabase.auth.onAuthStateChange((event, session) => {
      if (!SESSION_EVENTS.has(event)) {
        return;
      }
      if (event === "SIGNED_OUT") {
        setHasSession(false);
        return;
      }
      setHasSession(Boolean(session?.access_token));
    });

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, []);

  const signOut = useCallback(async () => {
    const supabase = createClient();
    await supabase.auth.signOut();
    setHasSession(false);
    window.location.assign("/");
  }, []);

  return { hasSession, signOut };
}

export function AuthNavDesktop() {
  const { hasSession, signOut } = useHasSession();

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
        <button
          type="button"
          onClick={() => void signOut()}
          className="text-sm font-medium text-zinc-600 hover:text-zinc-900"
        >
          Sign out
        </button>
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
  const { hasSession, signOut } = useHasSession();

  if (hasSession === null) {
    return <span className="inline-block h-4 w-16" aria-hidden />;
  }

  if (hasSession) {
    return (
      <div className="flex items-center gap-3">
        <Link href="/portfolio" className="text-sm font-semibold text-blue-700">
          Account
        </Link>
        <button
          type="button"
          onClick={() => void signOut()}
          className="text-sm font-medium text-zinc-600"
        >
          Sign out
        </button>
      </div>
    );
  }

  return (
    <Link href="/sign-in" className="text-sm font-semibold text-blue-700">
      Sign in
    </Link>
  );
}
