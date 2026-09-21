import { useEffect, useState } from "react";
import { AreaChart } from "lucide-react";
import { getDatasetDistribution, getErrorMessage } from "../api/datasets";
import LoadingSpinner from "./LoadingSpinner";
import ErrorMessage from "./ErrorMessage";

const NUMERIC_TYPES = new Set(["integer", "float"]);

function Histogram({ bins }) {
  const maxCount = Math.max(...bins.map((b) => b.count), 1);

  return (
    <div className="flex h-48 items-end gap-0.5">
      {bins.map((bin, i) => (
        <div
          key={i}
          className="group relative flex-1"
          title={`${bin.range_start} – ${bin.range_end}: ${bin.count}`}
        >
          <div
            className="rounded-t-sm bg-brand-500 transition-all group-hover:bg-brand-600"
            style={{ height: `${Math.max((bin.count / maxCount) * 100, 2)}%` }}
          />
        </div>
      ))}
    </div>
  );
}

export default function DistributionsPanel({ dataset }) {
  const numericColumns = dataset.columns.filter((c) => NUMERIC_TYPES.has(c.inferred_type));
  const [column, setColumn] = useState(numericColumns[0]?.name ?? "");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!column) return;
    let cancelled = false;
    setLoading(true);
    setError(null);

    getDatasetDistribution(dataset.id, column)
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
  }, [dataset.id, column]);

  if (numericColumns.length === 0) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-5 text-sm text-slate-500 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-400">
        No numeric columns to show a distribution for.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-end gap-3 rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
        <label className="flex flex-col gap-1 text-xs font-medium text-slate-500 dark:text-slate-400">
          Column
          <select
            value={column}
            onChange={(e) => setColumn(e.target.value)}
            className="rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-sm text-slate-900 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
          >
            {numericColumns.map((c) => (
              <option key={c.name} value={c.name}>
                {c.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      {loading && <LoadingSpinner label="Computing distribution..." />}
      {error && <ErrorMessage message={error} />}

      {!loading && !error && result && (
        <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
          <div className="mb-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AreaChart className="h-4 w-4 text-brand-600 dark:text-brand-400" />
              <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
                Distribution of {result.column}
              </h3>
            </div>
            <div className="flex gap-4 text-xs text-slate-500 dark:text-slate-400">
              <span>min {result.min_value}</span>
              <span>mean {result.mean}</span>
              <span>max {result.max_value}</span>
            </div>
          </div>
          {result.bins.length === 0 ? (
            <p className="py-6 text-center text-sm text-slate-400">No data available.</p>
          ) : (
            <Histogram bins={result.bins} />
          )}
        </div>
      )}
    </div>
  );
}
