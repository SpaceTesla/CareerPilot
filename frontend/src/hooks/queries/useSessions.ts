import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";

export interface ResumeSession {
  session_id: string;
  user_id: string;
  profile_id: string;
  name: string;
  is_active: boolean;
  created_at: string | null;
  last_accessed_at: string | null;
}

export interface SessionListResponse {
  sessions: ResumeSession[];
  total: number;
}

export interface SessionDetailsResponse {
  session_id: string;
  user_id: string;
  profile_id: string;
  name: string;
  is_active: boolean;
  created_at: string | null;
  last_accessed_at: string | null;
  profile?: {
    name: string | null;
    email: string | null;
    summary: string | null;
  };
}

const STALE_TIME = 5 * 60 * 1000; // 5 minutes
const CACHE_TIME = 30 * 60 * 1000; // 30 minutes

/**
 * Hook to fetch all resume sessions for a user
 */
export function useResumeSessions(userId: string | null) {
  return useQuery({
    queryKey: ["sessions", "list", userId],
    queryFn: () =>
      apiRequest<SessionListResponse>(`/sessions?user_id=${userId}`),
    enabled: !!userId,
    staleTime: STALE_TIME,
    gcTime: CACHE_TIME,
  });
}

/**
 * Hook to fetch the active session
 */
export function useActiveSession(userId: string | null) {
  return useQuery({
    queryKey: ["sessions", "active", userId],
    queryFn: () =>
      apiRequest<{ session: SessionDetailsResponse | null }>(
        `/sessions/active?user_id=${userId}`
      ),
    enabled: !!userId,
    staleTime: STALE_TIME,
    gcTime: CACHE_TIME,
  });
}

/**
 * Hook to switch to a different session
 */
export function useSwitchSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      sessionId,
      userId,
    }: {
      sessionId: string;
      userId: string;
    }) => {
      return apiRequest<{
        success: boolean;
        message: string;
        session: SessionDetailsResponse;
      }>(`/sessions/switch/${sessionId}?user_id=${userId}`, {
        method: "POST",
      });
    },
    onSuccess: (data, variables) => {
      // Update localStorage with new session info
      if (data.session) {
        localStorage.setItem("cp_user_id", data.session.user_id);
        localStorage.setItem("cp_profile_id", data.session.profile_id);
        localStorage.setItem("cp_session_id", data.session.session_id);
      }

      // Invalidate all queries to refetch with new session data
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
      queryClient.invalidateQueries({ queryKey: ["analysis"] });
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      queryClient.invalidateQueries({ queryKey: ["interview"] });
      queryClient.invalidateQueries({ queryKey: ["resume"] });
    },
  });
}

/**
 * Hook to delete a session
 */
export function useDeleteSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (sessionId: string) =>
      apiRequest<{ success: boolean; message: string }>(
        `/sessions/${sessionId}`,
        { method: "DELETE" }
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
    },
  });
}
