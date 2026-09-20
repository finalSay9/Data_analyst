import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Rows3, Columns3, Database, FileText } from "lucide-react";
import { getDataset, getDatasetProfile } from "../api/datasets";
import { useApi } from "../hooks/useApi";
import LoadingSpinner from "../components/LoadingSpinner";
import ErrorMessage from "../components/ErrorMessage";
import StatusBadge from "../components/StatusBadge";
import StatCard from "../components/StatCard";
import ColumnProfileCard from "../components/ColumnProfileCard";

export default function DatasetDetailPage() {
  const { id } = useParams();

  const {
    data: dataset,
    loading: datasetLoading,
    error: datasetError,
  } = useApi(() => getDataset(id), [id]);

  const {
    data: profile,
    loading: profileLoading,
    error: profileError,
  } = useApi(() => getDatasetProfile(id), [id]);

  if (datasetLoading) return <LoadingSpinner label="Loading dataset..." />;
  if (datasetError) return <ErrorMessage message={datasetError} />;
  if (!dataset) return null;

  return (
    <div>
      <Link
        to="/"
        className="mb-4 inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to datasets
      </Link>

      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">
            {dataset.name}
          </h1>
          <p className="mt-1 flex items-center gap-1.5 text-sm text-slate-500 dark:text-slate-400">
            <FileText className="h-3.5 w-3.5" />
            {dataset.original_filename}
          </p>
        </div>
        <StatusBadge status={dataset.status} />
      </div>

      <div className="mb-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard label="Rows" value={dataset.row_count.toLocaleString()} icon={Rows3} />
        <StatCard label="Columns" value={dataset.columns.length} icon={Columns3} />
        <StatCard label="Table" value={dataset.table_name} icon={Database} accent="slate" />
        <StatCard
          label="Uploaded"
          value={new Date(dataset.created_at).toLocaleDateString()}
          icon={FileText}
          accent="slate"
        />
      </div>

      <h2 className="mb-4 text-lg font-semibold text-slate-900 dark:text-white">
        Column profile
      </h2>

      {profileLoading && <LoadingSpinner label="Computing profile..." />}
      {profileError && <ErrorMessage message={profileError} />}

      {!profileLoading && !profileError && profile && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {profile.columns.map((column) => (
            <ColumnProfileCard key={column.name} column={column} />
          ))}
        </div>
      )}
    </div>
  );
}
