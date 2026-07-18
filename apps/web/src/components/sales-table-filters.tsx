"use client";

import { FilterDropdown } from "@/components/filter-dropdown";
import { RegionFilterBar } from "@/components/region-filter-bar";
import {
  GRADE_COMPANY_FILTERS,
  gradeSubFilterOptions,
  isGradedCompany,
  type GradeCompanyFilter,
} from "@/lib/grade-filters";
import { formatSourceLabel, sourceFilterOptions } from "@/lib/sales-display";
import type { MarketRegionFilter } from "@/lib/market-regions";

type Props = {
  sources: string[];
  source: string;
  onSourceChange: (source: string) => void;
  gradeFilter: GradeCompanyFilter;
  gradeSub: string;
  onGradeFilterChange: (value: GradeCompanyFilter) => void;
  onGradeSubChange: (value: string) => void;
  availableGrades?: Iterable<string | null | undefined>;
  regionFilter: MarketRegionFilter;
  onRegionFilterChange: (value: MarketRegionFilter) => void;
};

const GRADE_OPTIONS = GRADE_COMPANY_FILTERS.map((f) => ({
  id: f.id,
  label: f.label,
}));

export function SalesTableFilters({
  sources,
  source,
  onSourceChange,
  gradeFilter,
  gradeSub,
  onGradeFilterChange,
  onGradeSubChange,
  availableGrades,
  regionFilter,
  onRegionFilterChange,
}: Props) {
  const sourceOptions = sourceFilterOptions(sources).map((s) => ({
    id: s,
    label: formatSourceLabel(s),
  }));

  const subOptions = isGradedCompany(gradeFilter)
    ? gradeSubFilterOptions(gradeFilter, availableGrades)
    : [];

  return (
    <div className="space-y-2">
      <style>{`
        .cc-sales-filters [data-filter-chip] {
          white-space: nowrap !important;
          border-radius: 999px !important;
          font-weight: 600 !important;
          letter-spacing: 0.04em;
        }
      `}</style>
      <div className="cc-sales-filters space-y-2">
        <RegionFilterBar value={regionFilter} onChange={onRegionFilterChange} uppercase />
        <div className="flex flex-wrap items-center gap-2">
          <div data-filter-chip>
            <FilterDropdown
              value={gradeFilter}
              onChange={(v) => {
                onGradeFilterChange(v);
                onGradeSubChange("");
              }}
              options={GRADE_OPTIONS}
              ariaLabel="Filter by grade company"
            />
          </div>
          {subOptions.length > 0 ? (
            <div data-filter-chip>
              <FilterDropdown
                value={gradeSub}
                onChange={onGradeSubChange}
                options={subOptions}
                ariaLabel="Filter by slab grade"
              />
            </div>
          ) : null}
          <div data-filter-chip>
            <FilterDropdown
              value={source}
              onChange={onSourceChange}
              options={sourceOptions}
              ariaLabel="Filter by marketplace"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
