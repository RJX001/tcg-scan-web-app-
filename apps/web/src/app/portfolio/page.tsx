import type { Metadata } from "next";
import { Hanken_Grotesk, IBM_Plex_Mono, Spectral } from "next/font/google";
import type { CSSProperties } from "react";
import { PortfolioClient } from "./portfolio-client";

const display = Spectral({ subsets: ["latin"], weight: ["700", "800"] });
const body = Hanken_Grotesk({ subsets: ["latin"], weight: ["400", "600", "700"] });
const mono = IBM_Plex_Mono({ subsets: ["latin"], weight: ["600", "700"] });

export const metadata: Metadata = {
  title: "Vault — CardChart",
  description:
    "Your collection, valued from live sold data — with verdicts on what to do next.",
};

export default function PortfolioPage() {
  const theme = {
    background: "#F7F6F2",
    minHeight: "100%",
    "--font-display": display.style.fontFamily,
    "--font-mono": mono.style.fontFamily,
  } as CSSProperties;

  return (
    <main className={`${body.className} mx-auto max-w-[1200px] px-6 py-10`} style={theme}>
      <PortfolioClient />
    </main>
  );
}
