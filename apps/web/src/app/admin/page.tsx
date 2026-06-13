import { AdminClient } from "./admin-client";

export default function AdminPage() {
  return (
    <main className="mx-auto max-w-6xl px-4 py-10">
      <h1 className="text-2xl font-bold tracking-tight">Owner dashboard</h1>
      <p className="mt-2 text-sm text-zinc-600">
        Monitor users, data freshness, and system health.
      </p>
      <div className="mt-8">
        <AdminClient />
      </div>
    </main>
  );
}
