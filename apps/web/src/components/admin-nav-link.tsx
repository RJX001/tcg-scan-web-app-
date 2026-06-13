"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getMe } from "@tcgscan/sdk-ts";

const ADMIN_ROLES = new Set(["admin", "admin_senior", "owner"]);

export function AdminNavLink({ className }: { className?: string }) {
  const [show, setShow] = useState(false);

  useEffect(() => {
    void getMe()
      .then((me) => setShow(ADMIN_ROLES.has(me.role ?? "user")))
      .catch(() => setShow(false));
  }, []);

  if (!show) return null;

  return (
    <Link href="/admin" className={className ?? "font-medium text-zinc-600 hover:text-zinc-900"}>
      Admin
    </Link>
  );
}
