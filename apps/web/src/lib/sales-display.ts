const SOURCE_ORDER = ["ebay", "tcgplayer", "cardmarket"] as const;

export function formatSourceLabel(source: string): string {
  if (source === "all") return "ALL MARKETPLACES";
  return source.toUpperCase();
}

export function formatGradeLabel(grade: string | null | undefined): string {
  const g = (grade ?? "raw").trim();
  return g ? g.toUpperCase() : "RAW";
}

export function sourceFilterOptions(available: string[]): string[] {
  const set = new Set(available.filter((s) => s !== "all"));
  const ordered: string[] = SOURCE_ORDER.filter((s) => set.has(s));
  for (const s of Array.from(set).sort()) {
    if (!ordered.includes(s)) ordered.push(s);
  }
  return ["all", ...ordered];
}
