import type { Metadata } from "next";
import { ShowcaseClient } from "./showcase-client";

export const metadata: Metadata = {
  title: "Showcase — TCG Scan",
  description: "Browse card artwork across every game we track.",
};

export default function ShowcasePage() {
  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <h1 className="text-2xl font-bold tracking-tight">Showcase</h1>
      <p className="mt-1 text-sm text-zinc-600">
        A visual browse of the catalog. Tap any card for prices and comps.
      </p>
      <div className="mt-6">
        <ShowcaseClient />
      </div>
    </main>
  );
}
