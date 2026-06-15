"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getMe } from "@tcgscan/sdk-ts";

import { isAdminRole } from "@/lib/auth/admin-access";
import { syncApiAuthFromSupabase } from "@/lib/auth/api-session";

export function MoreAdminLink() {
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
    <li>
      <Link
        href="/admin"
        className="flex items-center justify-between gap-3 px-4 py-4 hover:bg-zinc-50"
      >
        <div>
          <p className="font-semibold">Admin</p>
          <p className="text-xs text-zinc-500">Owner dashboard — users, health, revenue</p>
        </div>
        <span className="text-zinc-300">›</span>
      </Link>
    </li>
  );
}
