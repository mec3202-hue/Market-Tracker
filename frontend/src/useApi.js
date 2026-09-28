import { useEffect, useState } from "react";

/**
 * Run `fetcher` whenever `deps` change and track loading/error state.
 * The previous data stays available while a new request is in flight, and
 * responses from superseded requests are ignored.
 */
export function useApi(fetcher, deps) {
  const key = JSON.stringify(deps);
  const [state, setState] = useState({ key: null, data: null, error: null });

  useEffect(() => {
    let cancelled = false;
    fetcher()
      .then((data) => !cancelled && setState({ key, data, error: null }))
      .catch((error) => !cancelled && setState({ key, data: null, error }));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  const loading = state.key !== key;
  return { data: state.data, error: loading ? null : state.error, loading };
}
