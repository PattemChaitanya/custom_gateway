import { useState, useEffect, useRef, useCallback } from "react";

interface CacheEntry<T = unknown> {
  data: T;
  timestamp: number;
}

const cache = new Map<string, CacheEntry>();
const CACHE_TTL = 2 * 60 * 1000; // 2 minutes

export function useQueryCache<T>(
  key: string,
  fetcher: () => Promise<T>,
  options: { enabled?: boolean } = {},
) {
  const { enabled = true } = options;
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const [data, setData] = useState<T | undefined>(() => {
    const entry = cache.get(key);
    if (entry && Date.now() - entry.timestamp < CACHE_TTL) {
      return entry.data as T;
    }
    return undefined;
  });

  const [loading, setLoading] = useState<boolean>(() => {
    if (!enabled) return false;
    const entry = cache.get(key);
    return !(entry && Date.now() - entry.timestamp < CACHE_TTL);
  });

  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!enabled) return;

    const entry = cache.get(key);
    if (entry && Date.now() - entry.timestamp < CACHE_TTL) {
      setData(entry.data as T);
      setLoading(false);
      return;
    }

    let mounted = true;
    setLoading(true);
    setError(null);

    (async () => {
      try {
        const result = await fetcherRef.current();
        if (!mounted) return;
        cache.set(key, { data: result, timestamp: Date.now() });
        setData(result);
      } catch (err: any) {
        if (!mounted) return;
        setError(err.response?.data?.detail || err.message || String(err));
      } finally {
        if (mounted) setLoading(false);
      }
    })();

    return () => {
      mounted = false;
    };
  }, [key, enabled]);

  const refetch = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await fetcherRef.current();
      cache.set(key, { data: result, timestamp: Date.now() });
      setData(result);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || String(err));
    } finally {
      setLoading(false);
    }
  }, [key]);

  return { data, loading, error, refetch };
}

export function invalidateCache(key: string) {
  cache.delete(key);
}

export function invalidateCacheByPrefix(prefix: string) {
  for (const k of cache.keys()) {
    if (k.startsWith(prefix)) {
      cache.delete(k);
    }
  }
}
