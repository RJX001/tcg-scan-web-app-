import Link from "next/link";

import { ScanForm } from "./scan-form";

const scanEnabled =
  process.env.NODE_ENV !== "production" ||
  process.env.NEXT_PUBLIC_SCAN_ENABLED === "true";

export default function ScanPage() {
  return (
    <main className="mx-auto max-w-[1200px] px-6">
      {scanEnabled ? (
        <ScanForm />
      ) : (
        <div className="max-w-xl py-12">
          <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-[var(--eyebrow)]">
            Scan
          </p>
          <h1 className="font-display mt-2.5 text-4xl font-extrabold tracking-[-0.025em] leading-[1.05] text-[var(--text)]">
            Photo scan is rolling out soon
          </h1>
          <p className="mt-3.5 text-[15.5px] leading-relaxed text-[var(--text2)]">
            Use Search or Sales to look up any card and see cross-marketplace comps today.
          </p>
          <div className="mt-7 flex flex-wrap gap-3">
            <Link href="/market" className="cc-btn">
              Search cards
            </Link>
            <Link href="/sales" className="cc-btn-ghost">
              Browse sales
            </Link>
          </div>
        </div>
      )}
    </main>
  );
}
