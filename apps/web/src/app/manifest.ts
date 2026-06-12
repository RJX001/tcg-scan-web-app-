import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    id: "/",
    name: "TCG Scan — Price guide for every card",
    short_name: "TCG Scan",
    description:
      "Scan any trading card. Cross-marketplace comps, condition estimates, grading ROI, and the market ladder.",
    start_url: "/",
    scope: "/",
    display: "standalone",
    orientation: "portrait",
    background_color: "#ffffff",
    theme_color: "#1d4ed8",
    categories: ["finance", "utilities", "entertainment"],
    icons: [
      { src: "/icons/icon.svg", sizes: "any", type: "image/svg+xml", purpose: "any" },
      { src: "/icons/icon.svg", sizes: "any", type: "image/svg+xml", purpose: "maskable" },
    ],
    shortcuts: [
      { name: "Scan a card", url: "/scan" },
      { name: "Ladder", url: "/ladder" },
      { name: "Portfolio", url: "/portfolio" },
    ],
  };
}
