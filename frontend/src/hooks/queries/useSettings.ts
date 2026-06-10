import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";

const STALE_TIME = 5 * 60 * 1000; // 5 minutes

export type JobSearchStatus = "ACTIVE" | "PASSIVE" | "CLOSED";

export interface UserPreferences {
  job_search_status: JobSearchStatus;
  weekly_digest_enabled: boolean;
  digest_delivery_day: number;
  digest_delivery_hour: number;
  email_notifications: boolean;
  user_id: string;
}

export interface UserPreferencesUpdate {
  job_search_status: JobSearchStatus;
  weekly_digest_enabled: boolean;
  digest_delivery_day: number;
  digest_delivery_hour: number;
  email_notifications: boolean;
}

export interface CareerGoals {
  target_role: string;
  target_compensation_min: number;
  target_compensation_max: number;
  target_companies: string[];
  timeline_months: number;
  user_id: string;
}

export interface CareerGoalsUpdate {
  target_role: string;
  target_compensation_min: number;
  target_compensation_max: number;
  target_companies: string[];
  timeline_months: number;
}

// ── GET /identity/preferences ──────────────────────────────────────────────
export function usePreferences(userId: string | null) {
  return useQuery<UserPreferences>({
    queryKey: ["identity", "preferences", userId],
    queryFn: () => apiRequest<UserPreferences>("/api/v2/identity/preferences"),
    enabled: !!userId,
    staleTime: STALE_TIME,
  });
}

// ── PUT /identity/preferences ──────────────────────────────────────────────
export function useUpdatePreferences(userId: string | null) {
  const queryClient = useQueryClient();

  return useMutation<UserPreferences, Error, UserPreferencesUpdate>({
    mutationFn: (payload) =>
      apiRequest<UserPreferences>("/api/v2/identity/preferences", {
        method: "PUT",
        body: JSON.stringify(payload),
      }),
    onSuccess: (data) => {
      queryClient.setQueryData(["identity", "preferences", userId], data);
    },
  });
}

// ── GET /identity/goals ────────────────────────────────────────────────────
export function useGoals(userId: string | null) {
  return useQuery<CareerGoals>({
    queryKey: ["identity", "goals", userId],
    queryFn: () => apiRequest<CareerGoals>("/api/v2/identity/goals"),
    enabled: !!userId,
    staleTime: STALE_TIME,
  });
}

// ── PUT /identity/goals ────────────────────────────────────────────────────
export function useUpdateGoals(userId: string | null) {
  const queryClient = useQueryClient();

  return useMutation<CareerGoals, Error, CareerGoalsUpdate>({
    mutationFn: (payload) =>
      apiRequest<CareerGoals>("/api/v2/identity/goals", {
        method: "PUT",
        body: JSON.stringify(payload),
      }),
    onSuccess: (data) => {
      queryClient.setQueryData(["identity", "goals", userId], data);
      // Invalidate dashboard metrics as goals impact matching scores and deltas
      queryClient.invalidateQueries({ queryKey: ["analysis", "overview", userId] });
      queryClient.invalidateQueries({ queryKey: ["analysis", "job-match", userId] });
      queryClient.invalidateQueries({ queryKey: ["analysis", "skills-gap", userId] });
    },
  });
}
