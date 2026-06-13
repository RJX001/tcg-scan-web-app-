const COMPANY_STYLES: Record<string, string> = {
  PSA: "border-purple-300 bg-purple-50 text-purple-700",
  BGS: "border-blue-300 bg-blue-50 text-blue-700",
  SGC: "border-sky-300 bg-sky-50 text-sky-700",
  CGC: "border-teal-300 bg-teal-50 text-teal-700",
  ACE: "border-amber-300 bg-amber-50 text-amber-700",
};

export function GradeBadge({ grade }: { grade: string | null | undefined }) {
  const label = grade && grade.toLowerCase() !== "raw" ? grade : "Raw";
  const company = label.split(/[\s-]/)[0]?.toUpperCase() ?? "";
  const style = COMPANY_STYLES[company] ?? "border-zinc-300 bg-zinc-50 text-zinc-600";
  return (
    <span
      className={`inline-block rounded border px-1.5 py-0.5 text-[11px] font-semibold leading-none ${style}`}
    >
      {label}
    </span>
  );
}
