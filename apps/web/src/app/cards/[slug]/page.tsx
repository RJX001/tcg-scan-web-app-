import { redirect } from "next/navigation";

type Props = { params: Promise<{ slug: string }> };

/** Legacy path — canonical detail route is /card/[slug]. */
export default async function CardsSlugRedirectPage({ params }: Props) {
  const { slug } = await params;
  redirect(`/card/${slug}`);
}
