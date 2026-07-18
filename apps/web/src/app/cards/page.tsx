import { redirect } from "next/navigation";

/** Legacy /cards → Market IA. */
export default function CardsPage() {
  redirect("/market");
}
