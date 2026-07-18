"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

type Tab = {
  href: string;
  label: string;
  icon: (active: boolean) => React.ReactNode;
};

function stroke(active: boolean) {
  return active ? "var(--accent)" : "var(--text3)";
}

/** Mobile primary IA — subset of desktop nav with Scan as the center action. */
const TABS: Tab[] = [
  {
    href: "/market",
    label: "Market",
    icon: (a) => (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden>
        <path
          d="M4 19V5M4 19h16M8 15l3-4 3 2 4-6"
          stroke={stroke(a)}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    ),
  },
  {
    href: "/charts",
    label: "Charts",
    icon: (a) => (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden>
        <path
          d="M4 19h16M7 16V9M12 16V5M17 16v-4"
          stroke={stroke(a)}
          strokeWidth="2"
          strokeLinecap="round"
        />
      </svg>
    ),
  },
  {
    href: "/scan",
    label: "Scan",
    icon: () => (
      <svg width="26" height="26" viewBox="0 0 24 24" fill="none" aria-hidden>
        <path
          d="M4 8V6a2 2 0 0 1 2-2h2M16 4h2a2 2 0 0 1 2 2v2M20 16v2a2 2 0 0 1-2 2h-2M8 20H6a2 2 0 0 1-2-2v-2M3 12h18"
          stroke="var(--accent-ink)"
          strokeWidth="2"
          strokeLinecap="round"
        />
      </svg>
    ),
  },
  {
    href: "/listings",
    label: "Listings",
    icon: (a) => (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden>
        <path
          d="M5 8h14l-1.2 11.1a2 2 0 0 1-2 1.9H8.2a2 2 0 0 1-2-1.9L5 8Zm3 0V6a4 4 0 1 1 8 0v2"
          stroke={stroke(a)}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    ),
  },
  {
    href: "/vault",
    label: "Vault",
    icon: (a) => (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden>
        <path
          d="M4 7a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V7Z"
          stroke={stroke(a)}
          strokeWidth="2"
        />
        <path
          d="M8 11h8M8 15h5"
          stroke={stroke(a)}
          strokeWidth="2"
          strokeLinecap="round"
        />
      </svg>
    ),
  },
];

export function BottomNav() {
  const pathname = usePathname();
  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-40 border-t border-[var(--border)] bg-[var(--surface)]/95 backdrop-blur sm:hidden"
      style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
      aria-label="Primary"
    >
      <ul className="mx-auto grid max-w-md grid-cols-5">
        {TABS.map((tab) => {
          const active = pathname === tab.href || pathname.startsWith(`${tab.href}/`);
          if (tab.href === "/scan") {
            return (
              <li key={tab.href} className="relative flex justify-center">
                <Link
                  href={tab.href}
                  aria-label="Scan a card"
                  className="-mt-5 flex h-14 w-14 items-center justify-center rounded-full transition-transform active:scale-95"
                  style={{
                    background: "var(--accent)",
                    boxShadow: "0 0 0 4px var(--bg), var(--shadow-lg)",
                  }}
                >
                  {tab.icon(active)}
                </Link>
              </li>
            );
          }
          return (
            <li key={tab.href}>
              <Link
                href={tab.href}
                className="flex flex-col items-center gap-0.5 py-2"
                aria-current={active ? "page" : undefined}
              >
                {tab.icon(active)}
                <span
                  className="text-[10px] font-medium"
                  style={{ color: active ? "var(--accent)" : "var(--text3)" }}
                >
                  {tab.label}
                </span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
