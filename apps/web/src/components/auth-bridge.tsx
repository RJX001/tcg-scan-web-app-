"use client";

import { setAuthTokenGetter } from "@tcgscan/sdk-ts";
import { useEffect } from "react";

import { createClient } from "@/lib/supabase/browser";

export function SupabaseAuthBridge() {
  useEffect(() => {
    const supabase = createClient();

    setAuthTokenGetter(async () => {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      return session?.access_token ?? null;
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(() => {
      // Token getter reads fresh session on each API call.
    });

    return () => subscription.unsubscribe();
  }, []);

  return null;
}
