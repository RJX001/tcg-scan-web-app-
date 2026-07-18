import type { ConditionEstimate } from "@tcgscan/sdk-ts";

const SUBGRADES: { key: keyof ConditionEstimate; label: string }[] = [
  { key: "centering", label: "Centering" },
  { key: "corners", label: "Corners" },
  { key: "edges", label: "Edges" },
  { key: "surface", label: "Surface" },
];

const VERDICT_STYLE: Record<string, string> = {
  GRADE: "bg-[rgba(30,154,107,0.12)] text-[#1E9A6B] border-[rgba(30,154,107,0.25)]",
  SELL: "bg-[rgba(214,68,75,0.12)] text-[#D6444B] border-[rgba(214,68,75,0.25)]",
  HOLD: "bg-[rgba(182,134,46,0.10)] text-[#B6862E] border-[rgba(182,134,46,0.25)]",
  BUY: "bg-[rgba(30,154,107,0.12)] text-[#1E9A6B] border-[rgba(30,154,107,0.25)]",
};

function SubgradeBar({ label, value }: { label: string; value: number }) {
  const pct = Math.min(100, Math.max(0, (value / 10) * 100));
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs text-[#5B5F68]">
        <span>{label}</span>
        <span>{value.toFixed(1)}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-[#F1EFE9]">
        <div className="h-full rounded-full bg-[#B6862E]" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export function ConditionPanel({ condition }: { condition: ConditionEstimate }) {
  if (condition.overall == null) return null;

  const verdict = condition.verdict;

  return (
    <div className="rounded-[18px] border border-[#E4E1D8] bg-[#FFFFFF] p-4 shadow-[0_1px_2px_rgba(23,24,28,0.05)]">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#B6862E]">
            Condition estimate
          </p>
          <p className="mt-1 text-2xl font-bold text-[#17181C]">
            {condition.psa_label ?? "Analyzing…"}
          </p>
          <p className="text-sm text-[#5B5F68]">
            Overall {condition.overall.toFixed(1)}/10
            {condition.confidence != null && (
              <span className="ml-2 text-[#84878F]">
                · {(condition.confidence * 100).toFixed(0)}% confidence
              </span>
            )}
          </p>
        </div>
        {verdict && (
          <span
            className={`whitespace-nowrap rounded-full border px-3 py-1 text-sm font-semibold ${VERDICT_STYLE[verdict.action] ?? VERDICT_STYLE.HOLD}`}
          >
            {verdict.action}
          </span>
        )}
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        {SUBGRADES.map(({ key, label }) => {
          const v = condition[key];
          if (typeof v !== "number") return null;
          return <SubgradeBar key={key} label={label} value={v} />;
        })}
      </div>

      {verdict && (
        <p className="mt-4 text-sm leading-relaxed text-[#5B5F68]">{verdict.reason}</p>
      )}
    </div>
  );
}
