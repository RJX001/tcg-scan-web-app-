export type GradeCompanyFilter = "all" | "raw" | "PSA" | "BGS" | "CGC" | "ACE";

export const GRADE_COMPANY_FILTERS: { id: GradeCompanyFilter; label: string }[] = [
  { id: "all", label: "All grades" },
  { id: "raw", label: "Raw" },
  { id: "PSA", label: "PSA" },
  { id: "BGS", label: "Beckett (BGS)" },
  { id: "CGC", label: "CGC" },
  { id: "ACE", label: "ACE" },
];

export function isRawGrade(grade: string | null | undefined): boolean {
  const g = (grade ?? "raw").trim().toLowerCase();
  return g === "" || g === "raw" || g === "none";
}

export function gradeCompanyFromText(grade: string | null | undefined): GradeCompanyFilter | null {
  if (isRawGrade(grade)) return "raw";
  const upper = grade!.toUpperCase();
  if (upper.startsWith("PSA")) return "PSA";
  if (upper.startsWith("BGS") || upper.includes("BECKETT")) return "BGS";
  if (upper.startsWith("CGC")) return "CGC";
  if (upper.startsWith("ACE")) return "ACE";
  return null;
}

export function matchesGradeCompanyFilter(
  grade: string | null | undefined,
  filter: GradeCompanyFilter,
): boolean {
  if (filter === "all") return true;
  if (filter === "raw") return isRawGrade(grade);
  const company = gradeCompanyFromText(grade);
  return company === filter;
}
