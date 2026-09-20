import { TrendingUp, TrendingDown, Info } from "lucide-react";

const STRENGTH_LABEL = {
  strong: "Strong",
  moderate: "Moderate",
  weak: "Weak",
};

function cellStyle(value) {
  if (value === null || value === undefined) {
    return { backgroundColor: "transparent" };
  }
  // Teal for positive correlation, rose for negative, intensity scales
  // with magnitude. Diagonal (value === 1) gets the strongest teal.
  const intensity = Math.min(Math.abs(value), 1);
  const alpha = 0.12 + intensity * 0.75;

  return value >= 0
    ? { backgroundColor: `rgba(13, 148, 136, ${alpha})` } // teal-600
    : { backgroundColor: `rgba(225, 29, 72, ${alpha})` }; // rose-600
}

function textColorFor(value) {
  if (value === null || value === undefined) return "text-slate-300 dark:text-slate-700";
  return Math.abs(value) > 0.5
    ? "text-white font-medium"
    : "text-slate-700 dark:text-slate-200";
}

function Heatmap({ columns, matrix }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
      <table className="border-separate border-spacing-1">
        <thead>
          <tr>
            <th className="w-24" />
            {columns.map((col) => (
              <th
                key={col}
                className="max-w-16 truncate px-1 pb-2 text-left text-xs font-medium text-slate-500 dark:text-slate-400"
                title={col}
              >
                <div className="w-16 truncate -rotate-45 origin-left">{col}</div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {matrix.map((row, i) => (
            <tr key={columns[i]}>
              <th className="pr-2 text-right text-xs font-medium text-slate-500 dark:text-slate-400 whitespace-nowrap">
                {columns[i]}
              </th>
              {row.map((value, j) => (
                <td
                  key={j}
                  style={cellStyle(value)}
                  className={`h-10 w-10 rounded-md text-center align-middle text-xs ${textColorFor(value)}`}
                  title={`${columns[i]} × ${columns[j]}: ${value ?? "undefined"}`}
                >
                  {value !== null && value !== undefined ? value.toFixed(2) : "—"}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PairRow({ pair }) {
  const isPositive = pair.correlation >= 0;
  const Icon = isPositive ? TrendingUp : TrendingDown;

  return (
    <div className="flex items-center justify-between gap-3 border-b border-slate-100 py-2.5 last:border-0 dark:border-slate-800">
      <div className="flex min-w-0 items-center gap-2">
        <Icon
          className={`h-4 w-4 shrink-0 ${isPositive ? "text-brand-600 dark:text-brand-400" : "text-rose-600 dark:text-rose-400"}`}
        />
        <span className="truncate text-sm text-slate-700 dark:text-slate-200">
          {pair.column_a} <span className="text-slate-400">↔</span> {pair.column_b}
        </span>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500 dark:bg-slate-800 dark:text-slate-400">
          {STRENGTH_LABEL[pair.strength] ?? pair.strength}
        </span>
        <span className="w-14 text-right text-sm font-semibold text-slate-900 dark:text-white">
          {pair.correlation.toFixed(3)}
        </span>
      </div>
    </div>
  );
}

export default function CorrelationsPanel({ data }) {
  if (data.insufficient_columns) {
    return (
      <div className="flex items-start gap-3 rounded-xl border border-slate-200 bg-white p-5 text-sm text-slate-500 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-400">
        <Info className="h-4.5 w-4.5 shrink-0 text-slate-400" />
        <p>
          Needs at least two numeric columns to compute correlations. This dataset has{" "}
          {data.numeric_columns.length}.
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <Heatmap columns={data.numeric_columns} matrix={data.matrix} />

      <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
        <h3 className="mb-1 text-sm font-semibold text-slate-900 dark:text-white">
          Strongest relationships
        </h3>
        <p className="mb-2 text-xs text-slate-500 dark:text-slate-400">
          Ranked by absolute correlation strength
        </p>
        {data.pairs.length === 0 ? (
          <p className="py-6 text-center text-sm text-slate-400">
            No defined correlations (a column may have zero variance).
          </p>
        ) : (
          <div>
            {data.pairs.map((pair) => (
              <PairRow key={`${pair.column_a}-${pair.column_b}`} pair={pair} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
