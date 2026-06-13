import { describe, expect, it } from "vitest";
import { fmtSoldAtLocal } from "./format";

describe("fmtSoldAtLocal", () => {
  it("formats date and time for a fixed locale", () => {
    const formatted = fmtSoldAtLocal("2026-06-02T15:30:00.000Z", "en-US");
    expect(formatted).toMatch(/Jun/i);
    expect(formatted).toMatch(/2026/);
    expect(formatted).toMatch(/:/);
  });
});
