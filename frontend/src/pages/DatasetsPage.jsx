import { Link } from "react-router-dom";
import { Plus, Database } from "lucide-react";
import { listDatasets } from "../api/datasets";
import { useApi } from "../hooks/useApi";
import DatasetCard from "../components/DatasetCard";
import LoadingSpinner from "../components/LoadingSpinner";
import ErrorMessage from "../components/ErrorMessage";
import IconBadge from "../components/IconBadge";

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center gap-4 rounded-xl border border-dashed border-slate-300 py-20 text-center dark:border-slate-700">
      <IconBadge icon={Database} size="xl" color="slate" />
      <div>
        <p className="font-medium text-slate-900 dark:text-white">No datasets yet</p>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Upload a CSV or Excel file to get started.
        </p>
      </div>
      <Link
        to="/upload"
        className="inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-700"
      >
        <Plus className="h-4 w-4" />
        Upload dataset
      </Link>
    </div>
  );
}

export default function DatasetsPage() {
  const { data: datasets, loading, error, refetch } = useApi(listDatasets);

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">
            Datasets
          </h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            All uploaded datasets, ready to explore and profile.
          </p>
        </div>
        <Link
          to="/upload"
          className="hidden items-center gap-1.5 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-700 sm:inline-flex"
        >
          <Plus className="h-4 w-4" />
          Upload
        </Link>
      </div>

      {loading && <LoadingSpinner label="Loading datasets..." />}

      {error && !loading && (
        <div className="space-y-3">
          <ErrorMessage message={error} />
          <button
            onClick={refetch}
            className="text-sm font-medium text-brand-600 hover:underline"
          >
            Try again
          </button>
        </div>
      )}

      {!loading && !error && datasets?.length === 0 && <EmptyState />}

      {!loading && !error && datasets?.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {datasets.map((dataset) => (
            <DatasetCard key={dataset.id} dataset={dataset} />
          ))}
        </div>
      )}
    </div>
  );
}
