import { DigestClient } from "./digest-client";

export default function DigestPage() {
  return (
    <main className="mx-auto max-w-2xl px-4 py-10">
      <h1 className="text-2xl font-bold">Daily brief</h1>
      <p className="mt-2 text-sm text-zinc-600">
        Your morning market summary — portfolio movers, trending cards, and opportunities.
      </p>
      <div className="mt-8">
        <DigestClient />
      </div>
    </main>
  );
}
