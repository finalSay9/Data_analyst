import { AlertTriangle } from "lucide-react";

export default function ErrorMessage({ message }) {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-900/20 dark:text-red-400">
      <AlertTriangle className="h-4.5 w-4.5 shrink-0" />
      <p>{message}</p>
    </div>
  );
}
