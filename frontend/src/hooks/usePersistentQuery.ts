/**
 * Custom React Query hook wrapper with localStorage persistence.
 * Use this for queries that should be cached across page reloads.
 */

import { useQuery, UseQueryOptions, UseQueryResult } from "@tanstack/react-query";
import { useEffect } from "react";
import { 
  getCachedData, 
  setCachedData, 
  shouldPersistQuery 
} from "@/lib/query-persister";

/**
 * A wrapper around useQuery that persists results to localStorage.
 * Data is automatically restored on mount and saved on successful fetch.
 */
export function usePersistentQuery<TData = unknown, TError = Error>(
  options: UseQueryOptions<TData, TError, TData, unknown[]> & {
    queryKey: unknown[];
  }
): UseQueryResult<TData, TError> {
  const { queryKey, ...restOptions } = options;
  
  // Try to get cached data for initial state
  const cachedData = shouldPersistQuery(queryKey) 
    ? getCachedData<TData>(queryKey) 
    : undefined;
  
  const query = useQuery({
    ...restOptions,
    queryKey,
    // Use cached data as initial data if available
    initialData: cachedData,
    // If we have cached data, consider it fresh for a while
    initialDataUpdatedAt: cachedData ? Date.now() - 60000 : undefined,
  });
  
  // Persist successful query results
  useEffect(() => {
    if (query.isSuccess && query.data && shouldPersistQuery(queryKey)) {
      setCachedData(queryKey, query.data);
    }
  }, [query.isSuccess, query.data, queryKey]);
  
  return query;
}
