import { describe, expect, it } from "vitest";

describe("sdk-ts", () => {
  it("exports getHealth", async () => {
    const { getHealth } = await import("./index.js");
    expect(typeof getHealth).toBe("function");
  });
});
