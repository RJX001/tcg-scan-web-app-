import { AlertsClient } from "./alerts-client";

export default function AlertsPage() {
  return (
    <main className="mx-auto max-w-2xl px-4 py-10">
      <h1 className="text-2xl font-bold">Alerts</h1>
      <p className="mt-2 text-sm text-zinc-600">
        Get notified when a card crosses your price threshold (MonitorAgent polls via Temporal).
      </p>
      <div className="mt-8">
        <AlertsClient />
      </div>
    </main>
  );
}
