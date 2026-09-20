import { AlertTriangle, CheckCircle2, Info } from "lucide-react";

function BoundRow({ label, value }) {
  return (
    <div className="flex items-center justify-between text-xs">
      <span className="text-slate-500 dark:text-slate-400">{label}</span>
      <span className="font-mono font-medium text-slate-700 dark:text-slate-200">{value}</span>
    </div>
  );
}

function OutlierColumnCard({ column }) {
  const hasOutliers = column.outlier_count > 0;

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
      <div className="mb-3 flex items-center justify-between">
        <h4 className="text-sm font-semibold text-slate-900 dark:text-white">
          {column.column}
        </h4>
        {hasOutliers ? (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700 ring-1 ring-inset ring-amber-600/20 dark:bg-amber-900/30 dark:text-amber-400">
            <AlertTriangle className="h-3.5 w-3.5" />
            {column.outlier_count} outlier{column.outlier_count !== 1 ? "s" : ""}
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700 ring-1 ring-inset ring-emerald-600/20 dark:bg-emerald-900/30 dark:text-emerald-400">
            <CheckCircle2 className="h-3.5 w-3.5" />
            Clean
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 border-b border-slate-100 pb-3 dark:border-slate-800">
        <BoundRow label="Q1" value={column.q1} />
        <BoundRow label="Q3" value={column.q3} />
        <BoundRow label="IQR" value={column.iqr} />
        <BoundRow label="% outliers" value={`${column.outlier_percentage}%`} />
        <BoundRow label="Lower bound" value={column.lower_bound} />
        <BoundRow label="Upper bound" value={column.upper_bound} />
      </div>

      {hasOutliers && (
        <div className="pt-3">
          <p className="mb-2 text-xs font-medium text-slate-500 dark:text-slate-400">
            Worst offenders
          </p>
          <div className="space-y-1">
            {column.sample_outliers.map((point) => (
              <div
                key={point.row_id}
                className="flex items-center justify-between text-xs"
              >
                <span className="text-slate-500 dark:text-slate-400">Row #{point.row_id}</span>
                <span className="font-mono font-medium text-slate-900 dark:text-white">
                  {point.value}
                </span>
                <span className="text-slate-400">
                  +{point.distance_from_bound.toFixed(1)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function OutliersPanel({ data }) {
  if (!data.columns || data.columns.length === 0) {
    return (
      <div className="flex items-start gap-3 rounded-xl border border-slate-200 bg-white p-5 text-sm text-slate-500 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-400">
        <Info className="h-4.5 w-4.5 shrink-0 text-slate-400" />
        <p>No numeric columns to check for outliers.</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {data.columns.map((column) => (
        <OutlierColumnCard key={column.column} column={column} />
      ))}
    </div>
  );
}
