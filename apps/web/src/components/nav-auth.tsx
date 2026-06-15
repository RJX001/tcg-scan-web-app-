"use client";

import { useAuth, UserButton } from "@clerk/nextjs";
import Link from "next/link";

type NavAuthProps = {
  variant: "desktop" | "mobile";
};

export function NavAuth({ variant }: NavAuthProps) {
  const { isLoaded, isSignedIn } = useAuth();

  if (!isLoaded) {
    return null;
  }

  if (isSignedIn) {
    return <UserButton />;
  }

  if (variant === "desktop") {
    return (
      <Link
        href="/sign-in"
        className="rounded-full bg-blue-700 px-4 py-1.5 text-sm font-semibold text-white hover:bg-blue-800"
      >
        Sign in
      </Link>
    );
  }

  return (
    <Link href="/sign-in" className="text-sm font-semibold text-blue-700">
      Sign in
    </Link>
  );
}
