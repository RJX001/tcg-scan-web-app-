import type { ConditionEstimate } from "@tcgscan/sdk-ts";

const SUBGRADES: { key: keyof ConditionEstimate; label: string }[] = [
  { key: "centering", label: "Centering" },
  { key: "corners", label: "Corners" },
  { key: "edges", label: "Edges" },
  { key: "surface", label: "Surface" },
];

const VERDICT_STYLE: Record<string, string> = {
  GRADE: "bg-[var(--up-bg)] text-[var(--up)] border-[var(--up)]/25",
  SELL: "bg-[var(--down-bg)] text-[var(--down)] border-[var(--down)]/25",
  HOLD: "bg-[var(--hold-bg)] text-[var(--hold)] border-[var(--hold)]/25",
  BUY: "bg-[var(--up-bg)] text-[var(--up)] border-[var(--up)]/25",
};

function SubgradeBar({ label, value }: { label: string; value: number }) {
  const pct = Math.min(100, Math.max(0, (value / 10) * 100));
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs text-[var(--text2)]">
        <span>{label}</span>
        <span>{value.toFixed(1)}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-[var(--surface2)]">
        <div className="h-full rounded-full bg-[var(--accent)]" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export function ConditionPanel({ condition }: { condition: ConditionEstimate }) {
  if (condition.overall == null) return null;

  const verdict = condition.verdict;

  return (
    <div className="cc-card p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--eyebrow)]">
            Condition estimate
          </p>
          <p className="mt-1 text-2xl font-bold text-[var(--text)]">
            {condition.psa_label ?? "Analyzing…"}
          </p>
          <p className="text-sm text-[var(--text2)]">
            Overall {condition.overall.toFixed(1)}/10
            {condition.confidence != null && (
              <span className="ml-2 text-[var(--text3)]">
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
        <p className="mt-4 text-sm leading-relaxed text-[var(--text2)]">{verdict.reason}</p>
      )}
    </div>
  );
}
