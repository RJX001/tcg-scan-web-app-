"use client";

import {
  GRADE_COMPANY_FILTERS,
  type GradeCompanyFilter,
} from "@/lib/grade-filters";

type Props = {
  value: GradeCompanyFilter;
  onChange: (value: GradeCompanyFilter) => void;
};

export function GradeFilterBar({ value, onChange }: Props) {
  return (
    <div className="flex flex-wrap gap-2">
      {GRADE_COMPANY_FILTERS.map((f) => (
        <button
          key={f.id}
          type="button"
          onClick={() => onChange(f.id)}
          className={`rounded-full px-3 py-1 text-xs ${
            value === f.id ? "bg-zinc-900 text-white" : "bg-zinc-100 text-zinc-700"
          }`}
        >
          {f.label}
        </button>
      ))}
    </div>
  );
}
