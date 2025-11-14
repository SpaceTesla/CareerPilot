import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";
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
      let endpoint = `/analysis/skills-gap?user_id=${userId}`;
      if (targetRole) {
        endpoint += `&target_role=${encodeURIComponent(targetRole)}`;
      }
      return apiRequest<SkillsGap>(endpoint);
    },
    enabled: !!userId,
  });
}

export function useJobMatch(userId: string | null, role?: string) {
  return useQuery({
    queryKey: ["analysis", "job-match", userId, role],
    queryFn: () => {
      let endpoint = `/analysis/job-match?user_id=${userId}`;
      if (role) {
        endpoint += `&role=${encodeURIComponent(role)}`;
      }
      return apiRequest<JobMatch>(endpoint);
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

