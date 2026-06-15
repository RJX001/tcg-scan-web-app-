"use client";

import { SignUp } from "@clerk/nextjs";

export default function Page() {
  return (
    <main className="flex min-h-[70vh] items-center justify-center px-4 py-10">
      <SignUp />
    </main>
  );
}
