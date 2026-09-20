import { useEffect, useState } from "react";
import { Info, BarChart3 } from "lucide-react";
import { getDatasetAggregations, getErrorMessage } from "../api/datasets";
import LoadingSpinner from "./LoadingSpinner";
import ErrorMessage from "./ErrorMessage";

const FUNCTIONS = [
  { value: "count", label: "Count" },
  { value: "sum", label: "Sum" },
  { value: "mean", label: "Mean" },
  { value: "min", label: "Min" },
  { value: "max", label: "Max" },
  { value: "median", label: "Median" },
];

const NUMERIC_TYPES = new Set(["integer", "float"]);

function Select({ label, value, onChange, children }) {
  return (
    <label className="flex flex-col gap-1 text-xs font-medium text-slate-500 dark:text-slate-400">
      {label}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-sm text-slate-900 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
      >
        {children}
      </select>
    </label>
  );
}

function BarList({ groups }) {
  const maxAbsValue = Math.max(...groups.map((g) => Math.abs(g.value ?? 0)), 1);

  return (
    <div className="space-y-2">
      {groups.map((group) => {
        const widthPct = Math.min((Math.abs(group.value ?? 0) / maxAbsValue) * 100, 100);
        return (
          <div key={group.group_value} className="flex items-center gap-3">
            <span className="w-28 shrink-0 truncate text-xs text-slate-600 dark:text-slate-300">
              {group.group_value}
            </span>
            <div className="h-6 flex-1 overflow-hidden rounded-md bg-slate-100 dark:bg-slate-800">
              <div
                className="h-full rounded-md bg-brand-500 transition-all"
                style={{ width: `${widthPct}%` }}
              />
            </div>
            <span className="w-20 shrink-0 text-right text-xs font-medium text-slate-900 dark:text-white">
              {group.value ?? "—"}
            </span>
            <span className="w-14 shrink-0 text-right text-xs text-slate-400">
              n={group.row_count}
            </span>
          </div>
        );
      })}
    </div>
  );
}

export default function AggregationsPanel({ dataset }) {
  const numericColumns = dataset.columns.filter((c) => NUMERIC_TYPES.has(c.inferred_type));

  const [groupBy, setGroupBy] = useState(dataset.columns[0]?.name ?? "");
  const [func, setFunc] = useState("count");
  const [aggColumn, setAggColumn] = useState(numericColumns[0]?.name ?? "");

  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const needsAggColumn = func !== "count";

  useEffect(() => {
    if (!groupBy) return;
    if (needsAggColumn && !aggColumn) return;

    let cancelled = false;
    setLoading(true);
    setError(null);

    getDatasetAggregations(dataset.id, {
      groupBy,
      func,
      aggColumn: needsAggColumn ? aggColumn : undefined,
    })
      .then((data) => {
        if (!cancelled) setResult(data);
      })
      .catch((err) => {
        if (!cancelled) setError(getErrorMessage(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [dataset.id, groupBy, func, aggColumn, needsAggColumn]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3 rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
        <Select label="Group by" value={groupBy} onChange={setGroupBy}>
          {dataset.columns.map((c) => (
            <option key={c.name} value={c.name}>
              {c.name}
            </option>
          ))}
        </Select>

        <Select label="Function" value={func} onChange={setFunc}>
          {FUNCTIONS.map((f) => (
            <option key={f.value} value={f.value}>
              {f.label}
            </option>
          ))}
        </Select>

        {needsAggColumn && (
          <Select label="Column" value={aggColumn} onChange={setAggColumn}>
            {numericColumns.length === 0 && <option value="">No numeric columns</option>}
            {numericColumns.map((c) => (
              <option key={c.name} value={c.name}>
                {c.name}
              </option>
            ))}
          </Select>
        )}
      </div>

      {loading && <LoadingSpinner label="Aggregating..." />}
      {error && <ErrorMessage message={error} />}

      {!loading && !error && result?.too_many_groups && (
        <div className="flex items-start gap-3 rounded-xl border border-slate-200 bg-white p-5 text-sm text-slate-500 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-400">
          <Info className="h-4.5 w-4.5 shrink-0 text-slate-400" />
          <p>
            "{groupBy}" has {result.total_groups} distinct values — too many to show
            usefully. Try grouping by a column with fewer categories.
          </p>
        </div>
      )}

      {!loading && !error && result && !result.too_many_groups && (
        <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
          <div className="mb-3 flex items-center gap-2">
            <BarChart3 className="h-4 w-4 text-brand-600 dark:text-brand-400" />
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
              {FUNCTIONS.find((f) => f.value === func)?.label}
              {aggColumn && func !== "count" ? ` of ${aggColumn}` : ""} by {groupBy}
            </h3>
          </div>
          {result.groups.length === 0 ? (
            <p className="py-6 text-center text-sm text-slate-400">No groups found.</p>
          ) : (
            <BarList groups={result.groups} />
          )}
        </div>
      )}
    </div>
  );
}
