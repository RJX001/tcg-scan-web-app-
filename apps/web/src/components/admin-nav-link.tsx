"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getMe } from "@tcgscan/sdk-ts";

import { isAdminRole } from "@/lib/auth/admin-access";
import { syncApiAuthFromSupabase } from "@/lib/auth/api-session";

export function AdminNavLink({ className }: { className?: string }) {
  const [show, setShow] = useState(false);

  useEffect(() => {
    async function load() {
      const token = await syncApiAuthFromSupabase();
      if (!token) {
        setShow(false);
        return;
      }
      try {
        const me = await getMe();
        setShow(isAdminRole(me.role));
      } catch {
        setShow(false);
      }
    }
    void load();
  }, []);

  if (!show) return null;

  return (
    <Link href="/admin" className={className ?? "font-medium text-zinc-600 hover:text-zinc-900"}>
      Admin
    </Link>
  );
}
