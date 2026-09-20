import { Link } from "react-router-dom";
import { FileSpreadsheet, Rows3, Clock } from "lucide-react";
import StatusBadge from "./StatusBadge";

function formatRelativeTime(isoString) {
  const date = new Date(isoString);
  const diffMs = Date.now() - date.getTime();
  const diffMins = Math.round(diffMs / 60000);

  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.round(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.round(diffHours / 24);
  return `${diffDays}d ago`;
}

export default function DatasetCard({ dataset }) {
  return (
    <Link
      to={`/datasets/${dataset.id}`}
      className="group flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:border-brand-300 hover:shadow-md dark:border-slate-800 dark:bg-slate-900 dark:hover:border-brand-700"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="shrink-0 rounded-lg bg-brand-50 p-2 text-brand-600 dark:bg-brand-900/30 dark:text-brand-400">
            <FileSpreadsheet className="h-4.5 w-4.5" />
          </div>
          <h3 className="truncate font-semibold text-slate-900 dark:text-white group-hover:text-brand-700 dark:group-hover:text-brand-400">
            {dataset.name}
          </h3>
        </div>
        <StatusBadge status={dataset.status} />
      </div>

      <p className="truncate text-xs text-slate-500 dark:text-slate-400">
        {dataset.original_filename}
      </p>

      <div className="mt-1 flex items-center gap-4 text-xs text-slate-500 dark:text-slate-400">
        <span className="flex items-center gap-1">
          <Rows3 className="h-3.5 w-3.5" />
          {dataset.row_count.toLocaleString()} rows
        </span>
        <span className="flex items-center gap-1">
          <Clock className="h-3.5 w-3.5" />
          {formatRelativeTime(dataset.created_at)}
        </span>
      </div>
    </Link>
  );
}
