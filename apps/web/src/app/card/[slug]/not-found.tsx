import Link from "next/link";

export default function CardNotFound() {
  return (
    <main className="mx-auto max-w-lg px-4 py-16 text-center">
      <p className="text-sm font-medium uppercase tracking-wide text-zinc-500">Card not found</p>
      <h1 className="mt-2 text-2xl font-bold text-zinc-900">We could not find that card</h1>
      <p className="mt-3 text-sm text-zinc-600">
        The catalogue link may be outdated, or the card has not been imported yet.
      </p>
      <div className="mt-8 flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
        <Link
          href="/cards"
          className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800"
        >
          Browse catalogue
        </Link>
        <Link href="/scan" className="text-sm text-blue-700 hover:underline">
          Open scanner
        </Link>
      </div>
    </main>
  );
}
