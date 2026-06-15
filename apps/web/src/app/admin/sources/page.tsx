import { AdminSourcesClient } from "./sources-client";

export default function AdminSourcesPage() {
  return (
    <main className="mx-auto max-w-6xl px-4 py-10">
      <h1 className="text-2xl font-bold tracking-tight">Live data sources</h1>
      <p className="mt-2 text-sm text-zinc-600">
        Probe external TCG metadata and pricing integrations via the backend. Pricing for Dragon Ball and
        One Piece catalog metadata comes later from eBay, Cardmarket, and paid APIs.
      </p>
      <div className="mt-8">
        <AdminSourcesClient />
      </div>
    </main>
  );
}
