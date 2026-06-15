/** Backend Postgres roles that may access the admin dashboard. */
export const ADMIN_ROLES = new Set(["admin", "admin_senior", "owner"]);

export function isAdminRole(role: string | null | undefined): boolean {
  return ADMIN_ROLES.has(role ?? "user");
}
