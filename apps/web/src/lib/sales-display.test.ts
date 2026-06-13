import { describe, expect, it } from "vitest";
import { formatGradeLabel, formatSourceLabel, sourceFilterOptions } from "./sales-display";

describe("sales-display", () => {
  it("formats source labels in caps", () => {
    expect(formatSourceLabel("all")).toBe("ALL MARKETPLACES");
    expect(formatSourceLabel("ebay")).toBe("EBAY");
    expect(formatSourceLabel("tcgplayer")).toBe("TCGPLAYER");
  });

  it("formats grade labels in caps", () => {
    expect(formatGradeLabel(null)).toBe("RAW");
    expect(formatGradeLabel("psa 10")).toBe("PSA 10");
  });

  it("orders marketplace filters with ebay first", () => {
    expect(sourceFilterOptions(["cardmarket", "ebay", "tcgplayer"])).toEqual([
      "all",
      "ebay",
      "tcgplayer",
      "cardmarket",
    ]);
  });
});
