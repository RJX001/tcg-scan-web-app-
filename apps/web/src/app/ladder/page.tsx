import { redirect } from "next/navigation";

/** Legacy /ladder → Indexes IA. */
export default function LadderPage() {
  redirect("/indexes");
}
