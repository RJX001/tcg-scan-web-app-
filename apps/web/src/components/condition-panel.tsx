import type { ConditionEstimate } from "@tcgscan/sdk-ts";

const SUBGRADES: { key: keyof ConditionEstimate; label: string }[] = [
  { key: "centering", label: "Centering" },
  { key: "corners", label: "Corners" },
  { key: "edges", label: "Edges" },
  { key: "surface", label: "Surface" },
];

const VERDICT_STYLE: Record<string, string> = {
  GRADE: "bg-emerald-100 text-emerald-800 border-emerald-200",
  SELL: "bg-amber-100 text-amber-800 border-amber-200",
  HOLD: "bg-zinc-100 text-zinc-700 border-zinc-200",
  BUY: "bg-blue-100 text-blue-800 border-blue-200",
};

function SubgradeBar({ label, value }: { label: string; value: number }) {
  const pct = Math.min(100, Math.max(0, (value / 10) * 100));
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs text-zinc-600">
        <span>{label}</span>
        <span>{value.toFixed(1)}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-zinc-100">
        <div className="h-full rounded-full bg-zinc-800" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export function ConditionPanel({ condition }: { condition: ConditionEstimate }) {
  if (condition.overall == null) return null;

  const verdict = condition.verdict;

  return (
    <div className="rounded-xl border border-zinc-200 bg-gradient-to-br from-white to-zinc-50 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">
            Condition estimate
          </p>
          <p className="mt-1 text-2xl font-bold">{condition.psa_label ?? "Analyzing…"}</p>
          <p className="text-sm text-zinc-600">
            Overall {condition.overall.toFixed(1)}/10
            {condition.confidence != null && (
              <span className="ml-2 text-zinc-400">
                · {(condition.confidence * 100).toFixed(0)}% confidence
              </span>
            )}
          </p>
        </div>
        {verdict && (
          <span
            className={`rounded-full border px-3 py-1 text-sm font-semibold ${VERDICT_STYLE[verdict.action] ?? VERDICT_STYLE.HOLD}`}
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
        <p className="mt-4 text-sm leading-relaxed text-zinc-700">{verdict.reason}</p>
      )}
    </div>
  );
}
