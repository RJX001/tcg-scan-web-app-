import { describe, expect, it } from "vitest";

import { resolveStatusLoadError } from "./admin-sources-access";

describe("resolveStatusLoadError", () => {
  it("redirects on 401", () => {
    expect(resolveStatusLoadError("API error 401: Unauthorized")).toEqual({
      access: "unauthenticated",
      shouldRedirect: true,
    });
  });

  it("blocks on 403", () => {
    expect(resolveStatusLoadError("API error 403: Forbidden")).toEqual({
      access: "forbidden",
      shouldRedirect: false,
    });
  });

  it("keeps page usable on 500", () => {
    expect(resolveStatusLoadError('API error 500: {"detail":"Internal server error"}')).toEqual({
      access: "ready",
      shouldRedirect: false,
    });
  });
});
