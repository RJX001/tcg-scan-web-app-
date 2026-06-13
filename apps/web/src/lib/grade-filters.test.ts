import { describe, expect, it } from "vitest";
import {
  gradeCompanyFromText,
  gradeSubFilterOptions,
  isRawGrade,
  matchesGradeCompanyFilter,
  matchesGradeFilter,
} from "./grade-filters";

describe("grade-filters", () => {
  it("detects raw grades", () => {
    expect(isRawGrade(null)).toBe(true);
    expect(isRawGrade("raw")).toBe(true);
    expect(isRawGrade("PSA 9")).toBe(false);
  });

  it("maps grade text to grading companies", () => {
    expect(gradeCompanyFromText("PSA 10")).toBe("PSA");
    expect(gradeCompanyFromText("BGS 9.5")).toBe("BGS");
    expect(gradeCompanyFromText("CGC 9")).toBe("CGC");
    expect(gradeCompanyFromText("ACE 10")).toBe("ACE");
    expect(gradeCompanyFromText("raw")).toBe("raw");
  });

  it("filters comps and listings by grading company", () => {
    expect(matchesGradeCompanyFilter("PSA 9", "PSA")).toBe(true);
    expect(matchesGradeCompanyFilter("BGS 9.5", "BGS")).toBe(true);
    expect(matchesGradeCompanyFilter("CGC 8", "CGC")).toBe(true);
    expect(matchesGradeCompanyFilter("ACE 10", "ACE")).toBe(true);
    expect(matchesGradeCompanyFilter("raw", "PSA")).toBe(false);
    expect(matchesGradeCompanyFilter("PSA 9", "all")).toBe(true);
  });

  it("filters by specific slab grade when sub is set", () => {
    expect(matchesGradeFilter("PSA 10", "PSA", "PSA 10")).toBe(true);
    expect(matchesGradeFilter("PSA 9", "PSA", "PSA 10")).toBe(false);
    expect(matchesGradeFilter("BGS 9.5", "BGS", "BGS 9.5")).toBe(true);
    expect(matchesGradeFilter("BGS 10", "BGS", "")).toBe(true);
    expect(matchesGradeFilter("PSA 9", "PSA", "")).toBe(true);
  });

  it("builds sub-grade options for PSA and BGS", () => {
    const psa = gradeSubFilterOptions("PSA", ["PSA 9", "PSA 10"]);
    expect(psa[0]?.label).toBe("ALL PSA");
    expect(psa.map((o) => o.label)).toContain("PSA 10");
    expect(psa.map((o) => o.label)).toContain("PSA 9");

    const bgs = gradeSubFilterOptions("BGS");
    expect(bgs.map((o) => o.label)).toContain("BGS 9.5");
    expect(bgs.map((o) => o.label)).toContain("BGS 10");
  });
});
