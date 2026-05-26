import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TCG Scan — AI price intelligence for every card",
  description: "Scan any trading card. See cross-marketplace comps, condition grade, and grading ROI.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
