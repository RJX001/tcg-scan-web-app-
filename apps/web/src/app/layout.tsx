import type { Metadata, Viewport } from "next";
import { Hanken_Grotesk, IBM_Plex_Mono, Spectral } from "next/font/google";

import { SupabaseAuthBridge } from "@/components/auth-bridge";
import { BottomNav } from "@/components/bottom-nav";
import { DevBanner } from "@/components/dev-banner";
import { PwaRegister } from "@/components/pwa-register";
import { SiteHeader } from "@/components/site-header";
import { CurrencyProvider } from "@/lib/currency";
import { ThemeProvider } from "@/lib/theme";
import "./globals.css";

export const dynamic = "force-dynamic";

const spectral = Spectral({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
  variable: "--font-display",
  display: "swap",
});

const hanken = Hanken_Grotesk({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
  variable: "--font-body",
  display: "swap",
});

const ibmPlexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-num",
  display: "swap",
});

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: "CardChart — Price guide for every card",
  description:
    "Cross-marketplace comps for Pokémon, MTG, Yu-Gi-Oh!, sports and more. Charts, listings, and grading ROI.",
  applicationName: "CardChart",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "CardChart",
  },
  icons: {
    icon: [{ url: "/icons/icon.svg", type: "image/svg+xml" }],
    apple: [{ url: "/icons/apple-touch-icon.png", sizes: "180x180" }],
  },
  openGraph: {
    title: "CardChart — Price guide for every card",
    description:
      "Cross-marketplace comps, market indexes, and grading ROI for every trading card.",
    url: siteUrl,
    siteName: "CardChart",
  },
  formatDetection: { telephone: false },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#B6862E",
  viewportFit: "cover",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${spectral.variable} ${hanken.variable} ${ibmPlexMono.variable}`}
      suppressHydrationWarning
    >
      <body className="min-h-screen bg-[var(--bg)] text-[var(--text)] antialiased">
        <ThemeProvider>
          <CurrencyProvider>
            <PwaRegister />
            <SupabaseAuthBridge />
            <DevBanner />
            <SiteHeader />
            <div className="pb-24 sm:pb-0">{children}</div>
            <BottomNav />
          </CurrencyProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
