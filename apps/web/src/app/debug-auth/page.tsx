"use client";

import { useEffect, useState } from "react";

import { syncApiAuthFromSupabase } from "@/lib/auth/api-session";
import { createClient } from "@/lib/supabase/browser";

type DebugAuthState = {
  hasSession: boolean;
  hasAccessToken: boolean;
  email: string | null;
  cookieHasSbPrefix: boolean;
  localStorageSupabaseKeys: number;
  backendMeLoaded: boolean;
  backendEmail: string | null;
  backendRole: string | null;
  backendTier: string | null;
  backendStatusCode: number | null;
};

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function DebugAuthPage() {
  const [state, setState] = useState<DebugAuthState | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    async function load() {
      try {
        const supabase = createClient();
        const {
          data: { session },
        } = await supabase.auth.getSession();

        const token = await syncApiAuthFromSupabase();

        let backendMeLoaded = false;
        let backendEmail: string | null = null;
        let backendRole: string | null = null;
        let backendTier: string | null = null;
        let backendStatusCode: number | null = null;

        if (token) {
          const res = await fetch(`${apiBaseUrl}/v1/me`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          backendStatusCode = res.status;
          if (res.ok) {
            const me = (await res.json()) as {
              email?: string | null;
              role?: string;
              tier?: string;
            };
            backendMeLoaded = true;
            backendEmail = me.email ?? null;
            backendRole = me.role ?? null;
            backendTier = me.tier ?? null;
          }
        }

        const next: DebugAuthState = {
          hasSession: Boolean(session),
          hasAccessToken: Boolean(session?.access_token),
          email: session?.user?.email ?? null,
          cookieHasSbPrefix:
            typeof document !== "undefined" && document.cookie.includes("sb-"),
          localStorageSupabaseKeys:
            typeof localStorage !== "undefined"
              ? Object.keys(localStorage).filter(
                  (key) => key.includes("supabase") || key.startsWith("sb-"),
                ).length
              : 0,
          backendMeLoaded,
          backendEmail,
          backendRole,
          backendTier,
          backendStatusCode,
        };

        if (mounted) setState(next);
      } catch (err) {
        if (mounted) {
          setError(err instanceof Error ? err.message : "Failed to read auth state");
        }
      }
    }

    void load();
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <main className="mx-auto max-w-lg px-4 py-10">
      <h1 className="text-2xl font-bold">Debug auth</h1>
      <p className="mt-2 text-sm text-zinc-600">Temporary diagnostics — remove before production GA.</p>

      {error ? (
        <p className="mt-6 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
          {error}
        </p>
      ) : null}

      {state ? (
        <dl className="mt-6 space-y-3 rounded-xl border border-zinc-200 bg-white p-4 text-sm">
          <div className="flex justify-between gap-4">
            <dt className="text-zinc-600">hasSession</dt>
            <dd className="font-mono">{String(state.hasSession)}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-zinc-600">hasAccessToken</dt>
            <dd className="font-mono">{String(state.hasAccessToken)}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-zinc-600">user email</dt>
            <dd className="font-mono">{state.email ?? "—"}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-zinc-600">cookieHasSbPrefix</dt>
            <dd className="font-mono">{String(state.cookieHasSbPrefix)}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-zinc-600">localStorageSupabaseKeys</dt>
            <dd className="font-mono">{state.localStorageSupabaseKeys}</dd>
          </div>
          <div className="flex justify-between gap-4 border-t border-zinc-100 pt-3">
            <dt className="text-zinc-600">backendMeLoaded</dt>
            <dd className="font-mono">{String(state.backendMeLoaded)}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-zinc-600">backendEmail</dt>
            <dd className="font-mono">{state.backendEmail ?? "—"}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-zinc-600">backendRole</dt>
            <dd className="font-mono">{state.backendRole ?? "—"}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-zinc-600">backendTier</dt>
            <dd className="font-mono">{state.backendTier ?? "—"}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-zinc-600">backendStatusCode</dt>
            <dd className="font-mono">{state.backendStatusCode ?? "—"}</dd>
          </div>
        </dl>
      ) : (
        <p className="mt-6 text-sm text-zinc-600">Loading…</p>
      )}
    </main>
  );
}
