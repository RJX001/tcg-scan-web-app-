/** Format sold timestamp in the user's locale and local timezone. */
export function fmtSoldAtLocal(iso: string, locale?: string): string {
  return new Intl.DateTimeFormat(locale, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(iso));
}
