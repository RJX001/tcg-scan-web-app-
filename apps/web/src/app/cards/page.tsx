import { CardsClient } from "./cards-client";

export default function CardsPage() {
  return (
    <main className="mx-auto max-w-6xl px-4 py-10">
      <h1 className="text-2xl font-bold tracking-tight">Card catalogue</h1>
      <p className="mt-2 text-sm text-zinc-600">
        Search cards across supported games. Pricing comes from marketplace sources once approved — not
        from catalogue metadata APIs.
      </p>
      <div className="mt-8">
        <CardsClient />
      </div>
    </main>
  );
}
