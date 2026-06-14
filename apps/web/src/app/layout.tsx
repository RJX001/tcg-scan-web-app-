import Link from "next/link";
import type { Metadata, Viewport } from "next";
import {
  ClerkProvider,
  Show,
  UserButton,
} from "@clerk/nextjs";
import { AdminNavLink } from "@/components/admin-nav-link";
import { AuthBridge } from "@/components/auth-bridge";
import { BottomNav } from "@/components/bottom-nav";
import { DevBanner } from "@/components/dev-banner";
import { PwaRegister } from "@/components/pwa-register";
import { CurrencyProvider, CurrencySelect } from "@/lib/currency";
import "./globals.css";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: "TCG Chart — Price guide for every card",
  description:
    "Cross-marketplace comps for Pokémon, MTG, Yu-Gi-Oh!, sports and more. Ladder, shop, and grading ROI.",
  applicationName: "TCG Chart",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "TCG Chart",
  },
  icons: {
    icon: [{ url: "/icons/icon.svg", type: "image/svg+xml" }],
    apple: [{ url: "/icons/apple-touch-icon.png", sizes: "180x180" }],
  },
  openGraph: {
    title: "TCG Chart — Price guide for every card",
    description:
      "Cross-marketplace comps, market ladder, and grading ROI for every trading card.",
    url: siteUrl,
    siteName: "TCG Chart",
  },
  formatDetection: { telephone: false },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#1d4ed8",
  viewportFit: "cover",
};

const NAV = [
  { href: "/shop", label: "Shop" },
  { href: "/ladder", label: "Ladder" },
  { href: "/scan", label: "Scan" },
  { href: "/showcase", label: "Showcase" },
  { href: "/sales", label: "Sales" },
  { href: "/indexes", label: "Indexes" },
  { href: "/portfolio", label: "Collection" },
  { href: "/more", label: "More" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-zinc-50 text-zinc-900 antialiased">
        <ClerkProvider>
          <CurrencyProvider>
            <PwaRegister />
            <AuthBridge />
            <DevBanner />
            <header className="sticky top-0 z-30 hidden border-b border-zinc-200 bg-white/95 backdrop-blur sm:block">
              <nav className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
                <Link href="/" className="text-lg font-extrabold tracking-tight text-zinc-900">
                  TCG<span className="text-blue-700">Chart</span>
                </Link>
                <ul className="flex items-center gap-5 text-sm">
                  {NAV.map((item) => (
                    <li key={item.href}>
                      <Link
                        href={item.href}
                        className={
                          item.href === "/scan"
                            ? "rounded-full bg-blue-700 px-4 py-1.5 font-semibold text-white hover:bg-blue-800"
                            : "font-medium text-zinc-600 hover:text-zinc-900"
                        }
                      >
                        {item.label}
                      </Link>
                    </li>
                  ))}
                  <li>
                    <CurrencySelect />
                  </li>
                  <li>
                    <AdminNavLink />
                  </li>
                  <li>
                    <Show when="signed-out">
                      <Link
                        href="/sign-in"
                        className="rounded-full bg-blue-700 px-4 py-1.5 text-sm font-semibold text-white hover:bg-blue-800"
                      >
                        Sign in
                      </Link>
                    </Show>
                    <Show when="signed-in">
                      <UserButton afterSignOutUrl="/" />
                    </Show>
                  </li>
                </ul>
              </nav>
            </header>
            <header className="sticky top-0 z-30 border-b border-zinc-200 bg-white/95 backdrop-blur sm:hidden">
              <div className="flex items-center justify-between px-4 py-3">
                <Link href="/" className="text-lg font-extrabold tracking-tight text-zinc-900">
                  TCG<span className="text-blue-700">Chart</span>
                </Link>
                <div className="flex items-center gap-2">
                  <CurrencySelect />
                  <Show when="signed-out">
                    <Link href="/sign-in" className="text-sm font-semibold text-blue-700">
                      Sign in
                    </Link>
                  </Show>
                  <Show when="signed-in">
                    <UserButton afterSignOutUrl="/" />
                  </Show>
                  <Link href="/search" aria-label="Search" className="p-1 text-zinc-600">
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
            <div className="pb-24 sm:pb-0">{children}</div>
            <BottomNav />
          </CurrencyProvider>
        </ClerkProvider>
      </body>
    </html>
  );
}
