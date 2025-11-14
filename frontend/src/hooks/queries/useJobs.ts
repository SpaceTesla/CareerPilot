import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";
import { API_BASE } from "@/lib/config";
import type {
  JobRecommendations,
  SalaryInsights,
  Keywords,
} from "@/types/analysis";

export function useJobRecommendations(userId: string | null, limit = 10) {
  return useQuery({
    queryKey: ["jobs", "recommendations", userId, limit],
    queryFn: () =>
      apiRequest<JobRecommendations>(
        `/jobs/recommendations?user_id=${userId}&limit=${limit}`
      ),
    enabled: !!userId,
  });
}

export function useSalaryInsights(userId: string | null, location?: string) {
  return useQuery({
    queryKey: ["jobs", "salary-insights", userId, location],
    queryFn: () => {
      const url = new URL(`${API_BASE}/jobs/salary-insights`);
      url.searchParams.set("user_id", userId!);
      if (location) url.searchParams.set("location", location);
      return apiRequest<SalaryInsights>(url.pathname + url.search);
    },
    enabled: !!userId,
  });
}

export function useKeywords(userId: string | null, targetRole?: string) {
  return useQuery({
    queryKey: ["jobs", "keywords", userId, targetRole],
    queryFn: () => {
      const url = new URL(`${API_BASE}/jobs/keywords`);
      url.searchParams.set("user_id", userId!);
      if (targetRole) url.searchParams.set("target_role", targetRole);
      return apiRequest<Keywords>(url.pathname + url.search);
    },
    enabled: !!userId,
  });
}

