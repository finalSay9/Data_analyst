import { useCallback, useEffect, useState } from "react";
import { getErrorMessage } from "../api/datasets";

/**
 * Runs an async fetcher on mount (and whenever `deps` changes), tracking
 * loading/error/data state. Exposes `refetch` for manual re-triggering
 * (e.g. a "try again" button after an error).
 */
export function useApi(fetcher, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const run = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetcher();
      setData(result);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    run();
  }, [run]);

  return { data, loading, error, refetch: run };
}
