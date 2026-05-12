import { useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";
import {
  AutoFillStartResult,
  AutoFillTask,
  JobApplication,
  JobApplicationsResponse,
  ApplicationStatus,
} from "@/types/analysis";

const STALE_TIME = 2 * 60 * 1000; // 2 minutes – mutable data, no long caching

// ── List applications ──────────────────────────────────────────────────────

export function useApplications(
  userId: string | null,
  status?: ApplicationStatus
) {
  const queryKey = ["applications", userId, status ?? "all"];

  const query = useQuery<JobApplicationsResponse>({
    queryKey,
    queryFn: () => {
      const qs = status
        ? `/applications?user_id=${userId}&status=${status}`
        : `/applications?user_id=${userId}`;
      return apiRequest<JobApplicationsResponse>(qs);
    },
    enabled: !!userId,
    staleTime: STALE_TIME,
  });

  return query;
}

// ── Track a new application ────────────────────────────────────────────────

interface TrackApplicationPayload {
  user_id: string;
  job_title: string;
  company?: string;
  job_url?: string;
  source?: string;
  location?: string;
  status?: ApplicationStatus;
  notes?: string;
  job_data?: Record<string, unknown>;
}

export function useSaveApplication() {
  const queryClient = useQueryClient();

  return useMutation<JobApplication, Error, TrackApplicationPayload>({
    mutationFn: (payload) =>
      apiRequest<JobApplication>("/applications", {
        method: "POST",
        body: JSON.stringify(payload),
        headers: { "Content-Type": "application/json" },
      }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["applications", data.user_id] });
    },
  });
}

// ── Update application status / notes ─────────────────────────────────────

interface UpdateApplicationPayload {
  applicationId: string;
  userId: string;
  status?: ApplicationStatus;
  notes?: string;
}

export function useUpdateApplication() {
  const queryClient = useQueryClient();

  return useMutation<JobApplication, Error, UpdateApplicationPayload>({
    mutationFn: ({ applicationId, userId, status, notes }) =>
      apiRequest<JobApplication>(
        `/applications/${applicationId}?user_id=${userId}`,
        {
          method: "PATCH",
          body: JSON.stringify({ status, notes }),
          headers: { "Content-Type": "application/json" },
        }
      ),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["applications", variables.userId],
      });
    },
  });
}

// ── Delete application ─────────────────────────────────────────────────────

export function useDeleteApplication() {
  const queryClient = useQueryClient();

  return useMutation<{ deleted: boolean; id: string }, Error, { applicationId: string; userId: string }>({
    mutationFn: ({ applicationId, userId }) =>
      apiRequest<{ deleted: boolean; id: string }>(
        `/applications/${applicationId}?user_id=${userId}`,
        { method: "DELETE" }
      ),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["applications", variables.userId],
      });
    },
  });
}

// ── Playwright auto-fill ───────────────────────────────────────────────────

interface AutoFillPayload {
  user_id: string;
  job_url: string;
  job_title?: string;
  job_company?: string;
}

/** Start a background autofill task. Returns task_id immediately. */
export function useAutoFillApplication() {
  return useMutation<AutoFillStartResult, Error, AutoFillPayload>({
    mutationFn: (payload) =>
      apiRequest<AutoFillStartResult>("/applications/auto-fill", {
        method: "POST",
        body: JSON.stringify(payload),
        headers: { "Content-Type": "application/json" },
      }),
  });
}

/**
 * Poll a running autofill task until it reaches "done" or "error".
 * Refetches every 2 s while the task is still in-progress or awaiting confirmation.
 */
export function useAutoFillTask(taskId: string | null, userId: string | null) {
  return useQuery<AutoFillTask>({
    queryKey: ["autofill-task", taskId],
    queryFn: () =>
      apiRequest<AutoFillTask>(`/applications/auto-fill/${taskId}?user_id=${userId}`),
    enabled: !!taskId && !!userId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return 2000;
      const active = ["pending", "running", "awaiting_confirmation"];
      return active.includes(data.status) ? 2000 : false;
    },
    staleTime: 0,
  });
}

// ── Confirm or cancel a pending autofill submission ────────────────────────

interface ConfirmAutoFillPayload {
  taskId: string;
  userId: string;
  confirmed: boolean;
}

export function useConfirmAutoFill() {
  return useMutation<{ task_id: string; confirmed: boolean }, Error, ConfirmAutoFillPayload>({
    mutationFn: ({ taskId, userId, confirmed }) =>
      apiRequest<{ task_id: string; confirmed: boolean }>(
        `/applications/auto-fill/${taskId}/confirm`,
        {
          method: "POST",
          body: JSON.stringify({ user_id: userId, confirmed }),
          headers: { "Content-Type": "application/json" },
        }
      ),
  });
}

// ── Portal session management ──────────────────────────────────────────────

export interface PortalSession {
  portal: string;
  session_id: string;
  saved_at: string | null;
}

interface SessionStatusResponse {
  sessions: PortalSession[];
  total: number;
}

/** Check which portals have saved sessions for this user. */
export function useSessionStatus(userId: string | null) {
  return useQuery<SessionStatusResponse>({
    queryKey: ["session-status", userId],
    queryFn: () =>
      apiRequest<SessionStatusResponse>(`/applications/session/status?user_id=${userId}`),
    enabled: !!userId,
    staleTime: STALE_TIME,
  });
}

interface ImportSessionPayload {
  user_id: string;
  portal: string;
  cookies: unknown[];
}

interface ImportSessionResult {
  status: string;
  portal: string;
  session_id: string;
  cookies_imported: number;
  message: string;
}

/** Import cookies exported from a browser extension (EditThisCookie / Cookie-Editor). */
export function useImportSession() {
  const queryClient = useQueryClient();

  return useMutation<ImportSessionResult, Error, ImportSessionPayload>({
    mutationFn: (payload) =>
      apiRequest<ImportSessionResult>("/applications/session/import", {
        method: "POST",
        body: JSON.stringify(payload),
        headers: { "Content-Type": "application/json" },
      }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["session-status", variables.user_id] });
    },
  });
}

/** Delete a saved portal session. */
export function useDeleteSession() {
  const queryClient = useQueryClient();

  return useMutation<{ deleted: boolean; portal: string }, Error, { userId: string; portal: string }>({
    mutationFn: ({ userId, portal }) =>
      apiRequest<{ deleted: boolean; portal: string }>(
        `/applications/session/${portal}?user_id=${userId}`,
        { method: "DELETE" }
      ),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["session-status", variables.userId] });
    },
  });
}