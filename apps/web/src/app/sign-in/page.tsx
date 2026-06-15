import { Suspense } from "react";

import { SignInForm } from "./sign-in-form";

export default function SignInPage() {
  return (
    <main className="flex min-h-[70vh] items-center justify-center px-4 py-10">
      <Suspense fallback={<div className="text-sm text-zinc-600">Loading…</div>}>
        <SignInForm />
      </Suspense>
    </main>
  );
}
