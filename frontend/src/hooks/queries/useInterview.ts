import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";
import { API_BASE } from "@/lib/config";
import type { InterviewPrep, InterviewQuestions } from "@/types/analysis";

export function useInterviewPrep(userId: string | null, role?: string) {
  return useQuery({
    queryKey: ["interview", "prep", userId, role],
    queryFn: () => {
      const url = new URL(`${API_BASE}/interview/prep`);
      url.searchParams.set("user_id", userId!);
      if (role) url.searchParams.set("role", role);
      return apiRequest<InterviewPrep>(url.pathname + url.search);
    },
    enabled: !!userId,
  });
}

export function useInterviewQuestions(userId: string | null) {
  return useQuery({
    queryKey: ["interview", "questions", userId],
    queryFn: () =>
      apiRequest<InterviewQuestions>(
        `/interview/questions?user_id=${userId}`
      ),
    enabled: !!userId,
  });
}

