import { describe, expect, it } from "vitest";

import { isProtectedPath } from "./protected-routes";

describe("isProtectedPath", () => {
  it.each(["/portfolio", "/watchlist", "/alerts", "/account", "/admin", "/collection"])(
    "protects %s and its subpaths",
    (prefix) => {
      expect(isProtectedPath(prefix)).toBe(true);
      expect(isProtectedPath(`${prefix}/anything`)).toBe(true);
    },
  );

  it("protects /admin/sources", () => {
    expect(isProtectedPath("/admin/sources")).toBe(true);
  });

  it.each([
    "/",
    "/shop",
    "/cards",
    "/card/pokemon-base1-4-102",
    "/sales",
    "/indexes",
    "/sign-in",
    "/auth/callback",
    "/scan",
    "/search",
  ])("leaves public route %s unprotected", (path) => {
    expect(isProtectedPath(path)).toBe(false);
  });

  it("does not protect lookalike prefixes", () => {
    expect(isProtectedPath("/accounting")).toBe(false);
    expect(isProtectedPath("/administrator")).toBe(false);
  });
});
