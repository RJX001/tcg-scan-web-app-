"use client";

import Link from "next/link";

export function AuthNavDesktop() {
  return (
    <Link
      href="/portfolio"
      className="rounded-full bg-blue-700 px-4 py-1.5 text-sm font-semibold text-white hover:bg-blue-800"
    >
      Account
    </Link>
  );
}

export function AuthNavMobile() {
  return (
    <Link href="/portfolio" className="text-sm font-semibold text-blue-700">
      Account
    </Link>
  );
}
