export type GradeCompanyFilter = "all" | "raw" | "PSA" | "BGS" | "CGC" | "ACE";

export const GRADE_COMPANY_FILTERS: { id: GradeCompanyFilter; label: string }[] = [
  { id: "all", label: "ALL GRADES" },
  { id: "raw", label: "RAW" },
  { id: "PSA", label: "PSA" },
  { id: "BGS", label: "BECKETT (BGS)" },
  { id: "CGC", label: "CGC" },
  { id: "ACE", label: "ACE" },
];

/** Common slab grades per company — merged with grades present in the current table data. */
export const GRADE_SUB_PRESETS: Record<Exclude<GradeCompanyFilter, "all" | "raw">, string[]> = {
  PSA: ["PSA 10", "PSA 9", "PSA 8", "PSA 7"],
  BGS: ["BGS 10", "BGS 9.5", "BGS 9", "BGS 8.5"],
  CGC: ["CGC 10", "CGC 9.5", "CGC 9", "CGC 8.5"],
  ACE: ["ACE 10", "ACE 9", "ACE 8"],
};

const GRADED_COMPANIES = new Set<GradeCompanyFilter>(["PSA", "BGS", "CGC", "ACE"]);

export function isGradedCompany(filter: GradeCompanyFilter): filter is "PSA" | "BGS" | "CGC" | "ACE" {
  return GRADED_COMPANIES.has(filter);
}

export function isRawGrade(grade: string | null | undefined): boolean {
  const g = (grade ?? "raw").trim().toLowerCase();
  return g === "" || g === "raw" || g === "none";
}

export function normalizeGradeLabel(grade: string | null | undefined): string {
  if (isRawGrade(grade)) return "RAW";
  return grade!.trim().replace(/\s+/g, " ").toUpperCase();
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

export function matchesGradeFilter(
  grade: string | null | undefined,
  company: GradeCompanyFilter,
  sub: string = "",
): boolean {
  if (!matchesGradeCompanyFilter(grade, company)) return false;
  if (!sub.trim()) return true;
  return normalizeGradeLabel(grade) === normalizeGradeLabel(sub);
}

function companyAllLabel(company: GradeCompanyFilter): string {
  const entry = GRADE_COMPANY_FILTERS.find((f) => f.id === company);
  return entry ? `ALL ${entry.label}` : `ALL ${company}`;
}

/** Sub-grade dropdown options for PSA / BGS / CGC / ACE. */
export function gradeSubFilterOptions(
  company: GradeCompanyFilter,
  availableGrades?: Iterable<string | null | undefined>,
): { id: string; label: string }[] {
  if (!isGradedCompany(company)) return [];

  const presets = GRADE_SUB_PRESETS[company];
  const seen = new Set(presets.map((g) => normalizeGradeLabel(g)));
  const merged = [...presets];

  if (availableGrades) {
    for (const g of availableGrades) {
      if (gradeCompanyFromText(g) !== company || isRawGrade(g)) continue;
      const norm = normalizeGradeLabel(g);
      if (!seen.has(norm)) {
        seen.add(norm);
        merged.push(norm);
      }
    }
  }

  merged.sort((a, b) => {
    const num = (s: string) => {
      const m = s.match(/(\d+(?:\.\d+)?)/);
      return m ? Number(m[1]) : 0;
    };
    return num(b) - num(a);
  });

  return [
    { id: "", label: companyAllLabel(company) },
    ...merged.map((g) => ({ id: g, label: g.toUpperCase() })),
  ];
}
