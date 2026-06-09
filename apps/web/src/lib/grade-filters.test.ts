import { describe, expect, it } from "vitest";
import {
  gradeCompanyFromText,
  isRawGrade,
  matchesGradeCompanyFilter,
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
});
