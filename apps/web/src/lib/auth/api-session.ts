import { setAuthTokenGetter } from "@tcgscan/sdk-ts";

import { createClient } from "@/lib/supabase/browser";

/** Sync Supabase session access token into the SDK client before backend API calls. */
export async function syncApiAuthFromSupabase(): Promise<string | null> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  const token = session?.access_token ?? null;
  setAuthTokenGetter(async () => token);
  return token;
}
