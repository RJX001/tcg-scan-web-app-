"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getMe } from "@tcgscan/sdk-ts";

const ADMIN_ROLES = new Set(["admin", "admin_senior", "owner"]);

export function MoreAdminLink() {
  const [show, setShow] = useState(false);

  useEffect(() => {
    void getMe()
      .then((me) => setShow(ADMIN_ROLES.has(me.role ?? "user")))
      .catch(() => setShow(false));
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
