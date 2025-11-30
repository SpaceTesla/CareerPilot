import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { apiRequest } from "@/lib/api";
import { getCachedData, setCachedData } from "@/lib/query-persister";
import type {
  AnalysisOverview,
  ATSScore,
  SkillsGap,
  JobMatch,
  CareerPath,
} from "@/types/analysis";

// Cache times for better performance
const STALE_TIME = 10 * 60 * 1000; // 10 minutes - data considered fresh
const CACHE_TIME = 60 * 60 * 1000; // 60 minutes - keep in memory cache

export function useAnalysisOverview(userId: string | null) {
  const queryKey = ["analysis", "overview", userId];
  const cachedData = getCachedData<AnalysisOverview>(queryKey);
  
  const query = useQuery({
    queryKey,
    queryFn: () =>
      apiRequest<AnalysisOverview>(
        `/analysis/overview?user_id=${userId}`
      ),
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

export function useATSScore(userId: string | null) {
  const queryKey = ["analysis", "ats-score", userId];
  const cachedData = getCachedData<ATSScore>(queryKey);
  
  const query = useQuery({
    queryKey,
    queryFn: () =>
      apiRequest<ATSScore>(`/analysis/ats-score?user_id=${userId}`),
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

export function useSkillsGap(userId: string | null, targetRole?: string) {
  const queryKey = ["analysis", "skills-gap", userId, targetRole];
  const cachedData = getCachedData<SkillsGap>(queryKey);
  
  const query = useQuery({
    queryKey,
    queryFn: () => {
      let endpoint = `/analysis/skills-gap?user_id=${userId}`;
      if (targetRole) {
        endpoint += `&target_role=${encodeURIComponent(targetRole)}`;
      }
      return apiRequest<SkillsGap>(endpoint);
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

export function useJobMatch(userId: string | null, role?: string) {
  const queryKey = ["analysis", "job-match", userId, role];
  const cachedData = getCachedData<JobMatch>(queryKey);
  
  const query = useQuery({
    queryKey,
    queryFn: () => {
      let endpoint = `/analysis/job-match?user_id=${userId}`;
      if (role) {
        endpoint += `&role=${encodeURIComponent(role)}`;
      }
      return apiRequest<JobMatch>(endpoint);
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

export function useCareerPath(userId: string | null) {
  const queryKey = ["analysis", "career-path", userId];
  const cachedData = getCachedData<CareerPath>(queryKey);
  
  const query = useQuery({
    queryKey,
    queryFn: () =>
      apiRequest<CareerPath>(`/analysis/career-path?user_id=${userId}`),
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

