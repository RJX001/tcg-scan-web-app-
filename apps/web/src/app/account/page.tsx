import { AccountClient } from "./account-client";

export default function AccountPage() {
  return (
    <main className="mx-auto max-w-lg px-4 py-10">
      <h1 className="text-2xl font-bold">Account</h1>
      <p className="mt-2 text-sm text-zinc-600">Manage your plan and billing.</p>
      <div className="mt-8">
        <AccountClient />
      </div>
    </main>
  );
}
