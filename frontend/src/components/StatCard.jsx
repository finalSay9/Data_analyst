export default function StatCard({ label, value, icon: Icon, accent = "brand" }) {
  const accentClasses = {
    brand: "text-brand-600 bg-brand-50 dark:bg-brand-900/30 dark:text-brand-400",
    slate: "text-slate-600 bg-slate-100 dark:bg-slate-800 dark:text-slate-300",
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <div className="flex items-center gap-3">
        {Icon && (
          <div className={`rounded-lg p-2 ${accentClasses[accent]}`}>
            <Icon className="h-4 w-4" />
          </div>
        )}
        <div className="min-w-0">
          <p className="truncate text-xs font-medium text-slate-500 dark:text-slate-400">
            {label}
          </p>
          <p className="truncate text-lg font-semibold text-slate-900 dark:text-white">
            {value}
          </p>
        </div>
      </div>
    </div>
  );
}
