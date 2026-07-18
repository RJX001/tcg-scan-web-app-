import { redirect } from "next/navigation";

/** Legacy /shop → Listings IA. */
export default function ShopPage() {
  redirect("/listings");
}
