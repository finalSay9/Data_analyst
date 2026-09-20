import { useParams, Link } from "react-router-dom";
import { useState } from "react";
import { ArrowLeft, Rows3, Columns3, Database, FileText } from "lucide-react";
import { getDataset, getDatasetProfile, getDatasetCorrelations, getDatasetOutliers } from "../api/datasets";
import { useApi } from "../hooks/useApi";
import LoadingSpinner from "../components/LoadingSpinner";
import ErrorMessage from "../components/ErrorMessage";
import StatusBadge from "../components/StatusBadge";
import StatCard from "../components/StatCard";
import ColumnProfileCard from "../components/ColumnProfileCard";
import CorrelationsPanel from "../components/CorrelationsPanel";
import OutliersPanel from "../components/OutliersPanel";
import AggregationsPanel from "../components/AggregationsPanel";

const TABS = [
  { id: "profile", label: "Column profile" },
  { id: "correlations", label: "Correlations" },
  { id: "outliers", label: "Outliers" },
  { id: "aggregations", label: "Aggregations" },
];

export default function DatasetDetailPage() {
  const { id } = useParams();
  const [activeTab, setActiveTab] = useState("profile");

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

  const {
    data: correlations,
    loading: correlationsLoading,
    error: correlationsError,
  } = useApi(() => getDatasetCorrelations(id), [id]);

  const {
    data: outliers,
    loading: outliersLoading,
    error: outliersError,
  } = useApi(() => getDatasetOutliers(id), [id]);

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

      <div className="mb-4 flex gap-1 border-b border-slate-200 dark:border-slate-800">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`border-b-2 px-3 py-2 text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? "border-brand-600 text-brand-700 dark:text-brand-400"
                : "border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "profile" && (
        <>
          {profileLoading && <LoadingSpinner label="Computing profile..." />}
          {profileError && <ErrorMessage message={profileError} />}
          {!profileLoading && !profileError && profile && (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {profile.columns.map((column) => (
                <ColumnProfileCard key={column.name} column={column} />
              ))}
            </div>
          )}
        </>
      )}

      {activeTab === "correlations" && (
        <>
          {correlationsLoading && <LoadingSpinner label="Computing correlations..." />}
          {correlationsError && <ErrorMessage message={correlationsError} />}
          {!correlationsLoading && !correlationsError && correlations && (
            <CorrelationsPanel data={correlations} />
          )}
        </>
      )}

      {activeTab === "outliers" && (
        <>
          {outliersLoading && <LoadingSpinner label="Detecting outliers..." />}
          {outliersError && <ErrorMessage message={outliersError} />}
          {!outliersLoading && !outliersError && outliers && (
            <OutliersPanel data={outliers} />
          )}
        </>
      )}

      {activeTab === "aggregations" && <AggregationsPanel dataset={dataset} />}
    </div>
  );
}
