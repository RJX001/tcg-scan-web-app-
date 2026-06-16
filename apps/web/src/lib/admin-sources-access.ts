export type AdminSourcesAccessState = "unauthenticated" | "forbidden" | "ready";

export function resolveStatusLoadError(message: string): {
  access: AdminSourcesAccessState;
  shouldRedirect: boolean;
} {
  if (message.includes("API error 401")) {
    return { access: "unauthenticated", shouldRedirect: true };
  }
  if (message.includes("API error 403")) {
    return { access: "forbidden", shouldRedirect: false };
  }
  return { access: "ready", shouldRedirect: false };
}
