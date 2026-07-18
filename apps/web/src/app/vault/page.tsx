import { redirect } from "next/navigation";

/** Vault nav target — middleware protects /portfolio; /vault stays public and redirects. */
export default function VaultPage() {
  redirect("/portfolio");
}
