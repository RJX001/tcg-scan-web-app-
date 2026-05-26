import { ScanForm } from "./scan-form";
import Link from "next/link";

export default function ScanPage() {
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
