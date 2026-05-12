import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { apiRequest } from "@/lib/api";
import { API_BASE } from "@/lib/config";
import { getCachedData, setCachedData } from "@/lib/query-persister";
import type {
  JobRecommendations,
  SalaryInsights,
  Keywords,
} from "@/types/analysis";

// Cache times for better performance
const STALE_TIME = 10 * 60 * 1000; // 10 minutes - data considered fresh
const CACHE_TIME = 60 * 60 * 1000; // 60 minutes - keep in memory cache

export function useJobRecommendations(userId: string | null, limit = 10) {
  const queryKey = ["jobs", "recommendations", userId, limit];
  const cachedData = getCachedData<JobRecommendations>(queryKey);
  
  const query = useQuery({
    queryKey,
    queryFn: () =>
      apiRequest<JobRecommendations>(
        `/jobs/recommendations?user_id=${userId}&limit=${limit}`
      ),
    enabled: !!userId,
    staleTime: STALE_TIME,
    gcTime: CACHE_TIME,
    initialData: cachedData,
    initialDataUpdatedAt: cachedData ? Date.now() - 60000 : undefined,
  });
  
  // Persist to localStorage on success
  useEffect(() => {
    if (query.isSuccess && query.data) {
      setCachedData(queryKey, query.data);
    }
  }, [query.isSuccess, query.data]);
  
  return query;
}

export function useSalaryInsights(userId: string | null, location?: string) {
  const queryKey = ["jobs", "salary-insights", userId, location];
  const cachedData = getCachedData<SalaryInsights>(queryKey);
  
  const query = useQuery({
    queryKey,
    queryFn: () => {
      const url = new URL(`${API_BASE}/jobs/salary-insights`);
      url.searchParams.set("user_id", userId!);
      if (location) url.searchParams.set("location", location);
      return apiRequest<SalaryInsights>(url.pathname + url.search);
    },
    enabled: !!userId,
    staleTime: STALE_TIME,
    gcTime: CACHE_TIME,
    initialData: cachedData,
    initialDataUpdatedAt: cachedData ? Date.now() - 60000 : undefined,
  });
  
  useEffect(() => {
    if (query.isSuccess && query.data) {
      setCachedData(queryKey, query.data);
    }
  }, [query.isSuccess, query.data]);
  
  return query;
}

export function useKeywords(userId: string | null, targetRole?: string) {
  const queryKey = ["jobs", "keywords", userId, targetRole];
  const cachedData = getCachedData<Keywords>(queryKey);
  
  const query = useQuery({
    queryKey,
    queryFn: () => {
      const url = new URL(`${API_BASE}/jobs/keywords`);
      url.searchParams.set("user_id", userId!);
      if (targetRole) url.searchParams.set("target_role", targetRole);
      return apiRequest<Keywords>(url.pathname + url.search);
    },
    enabled: !!userId,
    staleTime: STALE_TIME,
    gcTime: CACHE_TIME,
    initialData: cachedData,
    initialDataUpdatedAt: cachedData ? Date.now() - 60000 : undefined,
  });
  
  useEffect(() => {
    if (query.isSuccess && query.data) {
      setCachedData(queryKey, query.data);
    }
  }, [query.isSuccess, query.data]);
  
  return query;
}

