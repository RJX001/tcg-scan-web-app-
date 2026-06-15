"use client";

import { setAuthTokenGetter } from "@tcgscan/sdk-ts";
import { useEffect } from "react";

import { createClient } from "@/lib/supabase/browser";

export function SupabaseAuthBridge() {
  useEffect(() => {
    const supabase = createClient();

    const applyTokenFromSession = async () => {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      const token = session?.access_token ?? null;
      setAuthTokenGetter(async () => token);
    };

    void applyTokenFromSession();

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === "SIGNED_OUT") {
        setAuthTokenGetter(async () => null);
        return;
      }
      const token = session?.access_token ?? null;
      setAuthTokenGetter(async () => token);
    });

    return () => subscription.unsubscribe();
  }, []);

  return null;
}
