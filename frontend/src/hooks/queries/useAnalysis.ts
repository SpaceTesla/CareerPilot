import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";
import { API_BASE } from "@/lib/config";
import type {
  AnalysisOverview,
  ATSScore,
  SkillsGap,
  JobMatch,
  CareerPath,
} from "@/types/analysis";

export function useAnalysisOverview(userId: string | null) {
  return useQuery({
    queryKey: ["analysis", "overview", userId],
    queryFn: () =>
      apiRequest<AnalysisOverview>(
        `/analysis/overview?user_id=${userId}`
      ),
    enabled: !!userId,
  });
}

export function useATSScore(userId: string | null) {
  return useQuery({
    queryKey: ["analysis", "ats-score", userId],
    queryFn: () =>
      apiRequest<ATSScore>(`/analysis/ats-score?user_id=${userId}`),
    enabled: !!userId,
  });
}

export function useSkillsGap(userId: string | null, targetRole?: string) {
  return useQuery({
    queryKey: ["analysis", "skills-gap", userId, targetRole],
    queryFn: () => {
      const url = new URL(`${API_BASE}/analysis/skills-gap`);
      url.searchParams.set("user_id", userId!);
      if (targetRole) url.searchParams.set("target_role", targetRole);
      return apiRequest<SkillsGap>(url.pathname + url.search);
    },
    enabled: !!userId,
  });
}

export function useJobMatch(userId: string | null, role?: string) {
  return useQuery({
    queryKey: ["analysis", "job-match", userId, role],
    queryFn: () => {
      const url = new URL(`${API_BASE}/analysis/job-match`);
      url.searchParams.set("user_id", userId!);
      if (role) url.searchParams.set("role", role);
      return apiRequest<JobMatch>(url.pathname + url.search);
    },
    enabled: !!userId,
  });
}

export function useCareerPath(userId: string | null) {
  return useQuery({
    queryKey: ["analysis", "career-path", userId],
    queryFn: () =>
      apiRequest<CareerPath>(`/analysis/career-path?user_id=${userId}`),
    enabled: !!userId,
  });
}

