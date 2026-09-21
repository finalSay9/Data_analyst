import {
  Hash,
  ToggleLeft,
  Calendar,
  Type,
  TrendingUp,
} from "lucide-react";

const TYPE_META = {
  integer: { icon: Hash, label: "Integer", color: "text-cyan-600 bg-cyan-50 dark:bg-cyan-900/30 dark:text-cyan-400" },
  float: { icon: TrendingUp, label: "Float", color: "text-purple-600 bg-purple-50 dark:bg-purple-900/30 dark:text-purple-400" },
  boolean: { icon: ToggleLeft, label: "Boolean", color: "text-emerald-600 bg-emerald-50 dark:bg-emerald-900/30 dark:text-emerald-400" },
  datetime: { icon: Calendar, label: "Datetime", color: "text-orange-600 bg-orange-50 dark:bg-orange-900/30 dark:text-orange-400" },
  string: { icon: Type, label: "String", color: "text-slate-600 bg-slate-100 dark:bg-slate-800 dark:text-slate-300" },
};

function StatRow({ label, value }) {
  if (value === null || value === undefined) return null;
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-slate-500 dark:text-slate-400">{label}</span>
      <span className="font-medium text-slate-900 dark:text-white">{value}</span>
    </div>
  );
}

function TypeSpecificStats({ column }) {
  switch (column.inferred_type) {
    case "integer":
    case "float":
      return (
        <>
          <StatRow label="Min" value={column.min_value} />
          <StatRow label="Max" value={column.max_value} />
          <StatRow label="Mean" value={column.mean} />
          <StatRow label="Median" value={column.median} />
          <StatRow label="Std dev" value={column.std_dev} />
        </>
      );
    case "boolean":
      return (
        <>
          <StatRow label="True" value={column.true_count} />
          <StatRow label="False" value={column.false_count} />
        </>
      );
    case "datetime":
      return (
        <>
          <StatRow
            label="Earliest"
            value={column.min_date && new Date(column.min_date).toLocaleDateString()}
          />
          <StatRow
            label="Latest"
            value={column.max_date && new Date(column.max_date).toLocaleDateString()}
          />
        </>
      );
    case "string":
      return column.top_values?.length > 0 ? (
        <div className="space-y-1.5">
          <p className="text-xs font-medium text-slate-500 dark:text-slate-400">
            Top values
          </p>
          {column.top_values.map((tv) => (
            <div key={tv.value} className="flex items-center gap-2 text-xs">
              <span className="min-w-0 flex-1 truncate text-slate-700 dark:text-slate-300">
                {tv.value}
              </span>
              <span className="shrink-0 text-slate-400">{tv.count}</span>
            </div>
          ))}
        </div>
      ) : null;
    default:
      return null;
  }
}

export default function ColumnProfileCard({ column }) {
  const meta = TYPE_META[column.inferred_type] ?? TYPE_META.string;
  const Icon = meta.icon;

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
      <div className="mb-3 flex items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <div className={`shrink-0 rounded-md p-1.5 ${meta.color}`}>
            <Icon className="h-3.5 w-3.5" />
          </div>
          <h4 className="truncate text-sm font-semibold text-slate-900 dark:text-white">
            {column.name}
          </h4>
        </div>
        <span className="shrink-0 text-xs text-slate-400">{meta.label}</span>
      </div>

      <div className="space-y-1.5 border-b border-slate-100 pb-3 dark:border-slate-800">
        <StatRow label="Nulls" value={`${column.null_count} (${column.null_percentage}%)`} />
        <StatRow label="Unique" value={column.unique_count} />
      </div>

      <div className="pt-3">
        <TypeSpecificStats column={column} />
      </div>
    </div>
  );
}
