import { useCallback, useEffect, useState } from "react";

export function useApiResource<T>(loader: () => Promise<T>, dependencies: readonly unknown[] = []) {
  const [data, setData] = useState<T>();
  const [error, setError] = useState<Error>();
  const [loading, setLoading] = useState(true);
  const reload = useCallback(async () => {
    setLoading(true); setError(undefined);
    try { setData(await loader()); } catch (caught) { setError(caught instanceof Error ? caught : new Error(String(caught))); }
    finally { setLoading(false); }
  }, dependencies); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { void reload(); }, [reload]);
  return { data, error, loading, reload };
}
