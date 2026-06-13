import Link from "next/link";
import { ScanForm } from "./scan-form";

const scanEnabled =
  process.env.NODE_ENV !== "production" ||
  process.env.NEXT_PUBLIC_SCAN_ENABLED === "true";

export default function ScanPage() {
  if (!scanEnabled) {
    return (
      <main className="mx-auto max-w-lg px-4 py-12">
        <Link href="/" className="text-sm text-zinc-500 hover:text-zinc-900">
          ← Home
        </Link>
        <h1 className="mt-6 text-2xl font-bold">Card scanner (beta)</h1>
        <p className="mt-2 text-sm text-zinc-600">
          Photo scan is rolling out soon. Use Search or the Ladder to look up any card
          and see cross-marketplace comps today.
        </p>
        <div className="mt-6 flex gap-3">
          <Link
            href="/search"
            className="rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800"
          >
            Search cards
          </Link>
          <Link
            href="/ladder"
            className="rounded-lg border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50"
          >
            Market ladder
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-lg px-4 py-12">
      <Link href="/" className="text-sm text-zinc-500 hover:text-zinc-900">
        ← Home
      </Link>
      <h1 className="mt-6 text-2xl font-bold">Card scanner</h1>
      <p className="mt-2 text-sm text-zinc-600">
        Upload a photo to identify a card and see market comps.
      </p>
      <div className="mt-6">
        <ScanForm />
      </div>
    </main>
  );
}
