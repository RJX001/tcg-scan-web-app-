import { redirect } from "next/navigation";

/** Legacy /showcase → Vault IA (Vault then redirects to protected /portfolio). */
export default function ShowcasePage() {
  redirect("/vault");
}
