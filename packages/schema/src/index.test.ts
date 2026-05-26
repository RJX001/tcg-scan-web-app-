import { describe, expect, it } from "vitest";
import { HealthResponseSchema } from "./generated/index.js";

describe("HealthResponseSchema", () => {
  it("parses ok", () => {
    const r = HealthResponseSchema.parse({ status: "ok", version: "0.0.0" });
    expect(r.status).toBe("ok");
  });
});
