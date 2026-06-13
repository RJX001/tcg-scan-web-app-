import type { MetadataRoute } from "next";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";
const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const STATIC_ROUTES = [
  "/",
  "/shop",
  "/ladder",
  "/sales",
  "/indexes",
  "/showcase",
  "/portfolio",
  "/watchlist",
  "/search",
  "/more",
];

type MoverRow = { card?: { slug?: string | null } };

async function fetchCardSlugs(): Promise<string[]> {
  try {
    const res = await fetch(`${apiUrl}/v1/market/movers?limit=200&sort=volume`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return [];
    const rows = (await res.json()) as MoverRow[];
    return rows.map((r) => r.card?.slug).filter((s): s is string => Boolean(s));
  } catch {
    return [];
  }
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date();
  const staticEntries: MetadataRoute.Sitemap = STATIC_ROUTES.map((path) => ({
    url: `${siteUrl}${path}`,
    lastModified: now,
    changeFrequency: path === "/" ? "daily" : "weekly",
    priority: path === "/" ? 1 : 0.7,
  }));

  const slugs = await fetchCardSlugs();
  const cardEntries: MetadataRoute.Sitemap = slugs.map((slug) => ({
    url: `${siteUrl}/card/${slug}`,
    lastModified: now,
    changeFrequency: "daily",
    priority: 0.8,
  }));

  return [...staticEntries, ...cardEntries];
}
