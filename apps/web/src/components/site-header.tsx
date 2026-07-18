"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { AdminNavLink } from "@/components/admin-nav-link";
import { AuthNavDesktop, AuthNavMobile } from "@/components/auth-nav";
import { CurrencySelect } from "@/lib/currency";
import { ThemeToggle } from "@/lib/theme";

export const NAV = [
  { href: "/market", label: "Market" },
  { href: "/charts", label: "Charts" },
  { href: "/scan", label: "Scan" },
  { href: "/sales", label: "Sales" },
  { href: "/listings", label: "Listings" },
  { href: "/vault", label: "Vault" },
  { href: "/indexes", label: "Indexes" },
  { href: "/insights", label: "Insights" },
] as const;

function BrandMark() {
  return (
    <Link
      href="/market"
      className="font-display flex items-center gap-2 text-[18px] font-extrabold tracking-[-0.02em] text-[var(--text)]"
    >
      <span
        className="inline-flex h-[30px] w-[30px] items-center justify-center rounded-[9px]"
        style={{ background: "var(--accent)" }}
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
          <path
            d="M4 18V6M4 18h16"
            stroke="var(--accent-ink)"
            strokeWidth="2.2"
            strokeLinecap="round"
          />
          <path
            d="M8 14l3-3 3 2 5-7"
            stroke="var(--accent-ink)"
            strokeWidth="2.2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </span>
      CardChart
    </Link>
  );
}

function NavLinks() {
  const pathname = usePathname();

  return (
    <ul className="ml-1.5 flex items-center gap-0.5">
      {NAV.map((item) => {
        const active =
          pathname === item.href || pathname.startsWith(`${item.href}/`);
        return (
          <li key={item.href}>
            <Link
              href={item.href}
              className="whitespace-nowrap rounded-[9px] px-[13px] py-2 text-[13.5px] font-semibold transition-colors"
              style={{
                color: active ? "var(--text)" : "var(--text2)",
                background: active ? "var(--surface2)" : "transparent",
              }}
              aria-current={active ? "page" : undefined}
            >
              {item.label}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}

export function SiteHeader() {
  return (
    <>
      {/* Desktop sticky nav — Daylight CardChart */}
      <header
        className="sticky top-0 z-60 hidden border-b border-[var(--border)] bg-[var(--surface)] sm:block"
        style={{ zIndex: 60 }}
      >
        <nav className="mx-auto flex max-w-[1200px] items-center gap-5 px-6 py-3">
          <BrandMark />
          <NavLinks />
          <div className="ml-auto flex items-center gap-2.5">
            <Link
              href="/market"
              className="flex w-[180px] items-center gap-2 rounded-[10px] border border-[var(--border)] bg-[var(--surface2)] px-3 py-2 text-[13px] text-[var(--text3)]"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
                <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
                <path d="m20 20-3-3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
              Search any card…
            </Link>
            <CurrencySelect className="rounded-[9px] border border-[var(--border)] bg-[var(--surface2)] px-2 py-1.5 text-xs font-bold text-[var(--text2)]" />
            <ThemeToggle />
            <AdminNavLink />
            <AuthNavDesktop />
          </div>
        </nav>
      </header>

      {/* Mobile top bar */}
      <header className="sticky top-0 z-30 border-b border-[var(--border)] bg-[var(--surface)] sm:hidden">
        <div className="flex items-center justify-between px-4 py-3">
          <BrandMark />
          <div className="flex items-center gap-2">
            <CurrencySelect className="rounded-[9px] border border-[var(--border)] bg-[var(--surface2)] px-2 py-1 text-xs font-bold text-[var(--text2)]" />
            <ThemeToggle />
            <AuthNavMobile />
            <Link href="/market" aria-label="Search" className="p-1 text-[var(--text2)]">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden>
                <path
                  d="M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16Zm10 2-4.35-4.35"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                />
              </svg>
            </Link>
          </div>
        </div>
      </header>
    </>
  );
}
