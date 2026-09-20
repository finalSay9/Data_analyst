import { useCallback, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { UploadCloud, FileSpreadsheet, X, CheckCircle2, AlertTriangle } from "lucide-react";
import { uploadDataset, getErrorMessage } from "../api/datasets";

const ACCEPTED_EXTENSIONS = [".csv", ".xlsx", ".xls"];

function isAcceptedFile(file) {
  const lower = file.name.toLowerCase();
  return ACCEPTED_EXTENSIONS.some((ext) => lower.endsWith(ext));
}

export default function UploadPage() {
  const navigate = useNavigate();
  const inputRef = useRef(null);

  const [file, setFile] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const handleFileSelect = useCallback((selected) => {
    setError(null);
    setResult(null);
    if (!selected) return;

    if (!isAcceptedFile(selected)) {
      setError(`Unsupported file type. Allowed: ${ACCEPTED_EXTENSIONS.join(", ")}`);
      return;
    }
    setFile(selected);
  }, []);

  const handleDrop = useCallback(
    (e) => {
      e.preventDefault();
      setDragActive(false);
      const dropped = e.dataTransfer.files?.[0];
      handleFileSelect(dropped);
    },
    [handleFileSelect]
  );

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError(null);
    setProgress(0);

    try {
      const response = await uploadDataset(file, { onProgress: setProgress });
      setResult(response);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setUploading(false);
    }
  };

  const reset = () => {
    setFile(null);
    setResult(null);
    setError(null);
    setProgress(0);
    if (inputRef.current) inputRef.current.value = "";
  };

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">
          Upload dataset
        </h1>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          CSV or Excel files are parsed, type-inferred, and loaded into a real table.
        </p>
      </div>

      {!result && (
        <>
          {/* Dropzone */}
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragActive(true);
            }}
            onDragLeave={() => setDragActive(false)}
            onDrop={handleDrop}
            onClick={() => inputRef.current?.click()}
            className={`flex cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed p-12 text-center transition-colors ${
              dragActive
                ? "border-brand-500 bg-brand-50 dark:bg-brand-900/20"
                : "border-slate-300 hover:border-brand-400 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-900"
            }`}
          >
            <input
              ref={inputRef}
              type="file"
              accept={ACCEPTED_EXTENSIONS.join(",")}
              className="hidden"
              onChange={(e) => handleFileSelect(e.target.files?.[0])}
            />
            <div className="rounded-full bg-brand-50 p-3 dark:bg-brand-900/30">
              <UploadCloud className="h-6 w-6 text-brand-600 dark:text-brand-400" />
            </div>
            <div>
              <p className="font-medium text-slate-900 dark:text-white">
                Drop a file here, or click to browse
              </p>
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                Supports {ACCEPTED_EXTENSIONS.join(", ")}
              </p>
            </div>
          </div>

          {/* Selected file preview */}
          {file && (
            <div className="mt-4 flex items-center justify-between rounded-lg border border-slate-200 bg-white p-3 dark:border-slate-800 dark:bg-slate-900">
              <div className="flex min-w-0 items-center gap-3">
                <FileSpreadsheet className="h-5 w-5 shrink-0 text-brand-600 dark:text-brand-400" />
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-slate-900 dark:text-white">
                    {file.name}
                  </p>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    {(file.size / 1024).toFixed(1)} KB
                  </p>
                </div>
              </div>
              {!uploading && (
                <button
                  onClick={reset}
                  className="shrink-0 rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800"
                  aria-label="Remove file"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>
          )}

          {uploading && (
            <div className="mt-4">
              <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800">
                <div
                  className="h-full rounded-full bg-brand-600 transition-all duration-150"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <p className="mt-2 text-center text-xs text-slate-500 dark:text-slate-400">
                Uploading and ingesting... {progress}%
              </p>
            </div>
          )}

          {error && (
            <div className="mt-4 flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-900/20 dark:text-red-400">
              <AlertTriangle className="h-4.5 w-4.5 shrink-0" />
              <p>{error}</p>
            </div>
          )}

          <button
            onClick={handleUpload}
            disabled={!file || uploading}
            className="mt-6 w-full rounded-lg bg-brand-600 py-2.5 text-sm font-medium text-white transition-colors hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {uploading ? "Uploading..." : "Upload and ingest"}
          </button>
        </>
      )}

      {/* Result summary */}
      {result && (
        <div className="rounded-xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center gap-3">
            <div className="rounded-full bg-emerald-50 p-2 dark:bg-emerald-900/30">
              <CheckCircle2 className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
            </div>
            <div>
              <p className="font-semibold text-slate-900 dark:text-white">
                {result.dataset.name}
              </p>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                {result.inserted_count.toLocaleString()} rows ingested
              </p>
            </div>
          </div>

          {result.failed_rows?.length > 0 && (
            <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-900/50 dark:bg-amber-900/20 dark:text-amber-400">
              {result.failed_rows.length} row(s) failed to insert and were skipped.
            </div>
          )}

          <div className="mt-5 flex gap-3">
            <button
              onClick={() => navigate(`/datasets/${result.dataset.id}`)}
              className="flex-1 rounded-lg bg-brand-600 py-2.5 text-sm font-medium text-white transition-colors hover:bg-brand-700"
            >
              View dataset
            </button>
            <button
              onClick={reset}
              className="rounded-lg border border-slate-300 px-4 py-2.5 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              Upload another
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
