import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";
import type {
  AgentApprovalRequest,
  AgentDecisionLog,
  ApplicationExecutionLogs,
  WorkflowExecutionLog,
} from "@/types/analysis";

const STALE_TIME = 2 * 60 * 1000; // 2 minutes

// ── GET /approvals/pending ──────────────────────────────────────────────────
export function usePendingApprovals(userId: string | null) {
  return useQuery<AgentApprovalRequest[]>({
    queryKey: ["agent", "approvals", "pending", userId],
    queryFn: () => apiRequest<AgentApprovalRequest[]>("/approvals/pending"),
    enabled: !!userId,
    refetchInterval: 10000, // Poll for approvals every 10 seconds
  });
}

// ── POST /approvals/{approval_id}/action ────────────────────────────────────
interface ApprovalActionPayload {
  approvalId: string;
  action: "approved" | "rejected" | "modified";
  editedPayload?: Record<string, any>;
}

export function useSubmitApprovalAction(userId: string | null) {
  const queryClient = useQueryClient();

  return useMutation<{ status: string; message: string }, Error, ApprovalActionPayload>({
    mutationFn: ({ approvalId, action, editedPayload }) =>
      apiRequest<{ status: string; message: string }>(`/approvals/${approvalId}/action`, {
        method: "POST",
        body: JSON.stringify({
          action,
          edited_payload: editedPayload,
        }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agent", "approvals", "pending", userId] });
    },
  });
}

// ── GET /supervisor/sessions/{thread_id}/decisions ──────────────────────────
export function useSupervisorDecisions(threadId: string | null) {
  return useQuery<{ thread_id: string; decisions: AgentDecisionLog[] }>({
    queryKey: ["agent", "supervisor", "decisions", threadId],
    queryFn: () => apiRequest<{ thread_id: string; decisions: AgentDecisionLog[] }>(`/supervisor/sessions/${threadId}/decisions`),
    enabled: !!threadId,
  });
}

// ── POST /supervisor/approve ────────────────────────────────────────────────
interface SupervisorApprovePayload {
  threadId: string;
  decisionId: string;
  approved: boolean;
  userNotes?: string;
}

export function useSupervisorApprove() {
  return useMutation<{ status: string; next_node: string; message: string; run_id: string }, Error, SupervisorApprovePayload>({
    mutationFn: (payload) =>
      apiRequest<{ status: string; next_node: string; message: string; run_id: string }>("/supervisor/approve", {
        method: "POST",
        body: JSON.stringify({
          thread_id: payload.threadId,
          decision_id: payload.decisionId,
          approved: payload.approved,
          user_notes: payload.userNotes,
        }),
      }),
  });
}

// ── POST /agents/run ────────────────────────────────────────────────────────
interface RunAgentPayload {
  threadId: string;
  userMessage: string;
  bypassHumanGate?: boolean;
}

export function useStartAgentRun() {
  return useMutation<{ run_id: string; thread_id: string; status: string; message: string }, Error, RunAgentPayload>({
    mutationFn: (payload) =>
      apiRequest<{ run_id: string; thread_id: string; status: string; message: string }>("/agents/run", {
        method: "POST",
        body: JSON.stringify({
          thread_id: payload.threadId,
          user_message: payload.userMessage,
          bypass_human_gate: payload.bypassHumanGate ?? false,
        }),
      }),
  });
}

// ── GET /agents/session/{thread_id}/state ───────────────────────────────────
export function useAgentSessionState(threadId: string | null) {
  return useQuery<any>({
    queryKey: ["agent", "session", "state", threadId],
    queryFn: () => apiRequest<any>(`/agents/session/${threadId}/state`),
    enabled: !!threadId,
    refetchInterval: (query) => {
      const state = query.state.data;
      if (state && state.status === "processing") {
        return 3000; // Poll active state every 3 seconds
      }
      return false;
    },
  });
}

// ── GET /applications/{application_id}/logs (Wave 7) ─────────────────────────
export function useApplicationExecutionLogs(applicationId: string | null) {
  return useQuery<ApplicationExecutionLogs>({
    queryKey: ["applications", "logs", applicationId],
    queryFn: () => apiRequest<ApplicationExecutionLogs>(`/applications/${applicationId}/logs`),
    enabled: !!applicationId,
    refetchInterval: (query) => {
      // If there are running workflows, poll every 5s
      const data = query.state.data;
      if (data && data.browser_logs?.some((log) => log.status === "running")) {
        return 5000;
      }
      return false;
    },
  });
}

// ── GET /workflows/executions/{workflow_id} (Wave 7) ────────────────────────
export function useWorkflowStatus(workflowId: string | null) {
  return useQuery<WorkflowExecutionLog>({
    queryKey: ["workflows", "status", workflowId],
    queryFn: () => apiRequest<WorkflowExecutionLog>(`/workflows/executions/${workflowId}`),
    enabled: !!workflowId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data && ["RUNNING", "PENDING"].includes(data.status.toUpperCase())) {
        return 3000;
      }
      return false;
    },
  });
}

// ── POST /workflows/executions/{workflow_id}/cancel (Wave 7) ────────────────
export function useCancelWorkflow() {
  const queryClient = useQueryClient();

  return useMutation<{ workflow_id: string; message: string }, Error, string>({
    mutationFn: (workflowId) =>
      apiRequest<{ workflow_id: string; message: string }>(`/workflows/executions/${workflowId}/cancel`, {
        method: "POST",
      }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["workflows", "status", data.workflow_id] });
    },
  });
}
