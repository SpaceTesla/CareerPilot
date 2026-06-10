import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";
import type {
  EvaluationReport,
  BenchmarkReport,
  ModelRegistrationInfo,
} from "@/types/analysis";

const STALE_TIME = 5 * 60 * 1000; // 5 minutes

// ── POST /eval/run ──────────────────────────────────────────────────────────
interface TriggerEvalPayload {
  componentName: string;
  environment: string;
  commitSha?: string;
}

export function useTriggerEvalRun() {
  const queryClient = useQueryClient();

  return useMutation<{ eval_run_id: string; status: string; message: string }, Error, TriggerEvalPayload>({
    mutationFn: (payload) =>
      apiRequest<{ eval_run_id: string; status: string; message: string }>("/api/v2/eval/run", {
        method: "POST",
        body: JSON.stringify({
          component_name: payload.componentName,
          environment: payload.environment,
          commit_sha: payload.commitSha,
        }),
      }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["calibration", "eval", "report", data.eval_run_id] });
    },
  });
}

// ── GET /eval/runs/{run_id}/report ──────────────────────────────────────────
export function useEvalReport(runId: string | null) {
  return useQuery<EvaluationReport>({
    queryKey: ["calibration", "eval", "report", runId],
    queryFn: () => apiRequest<EvaluationReport>(`/api/v2/eval/runs/${runId}/report`),
    enabled: !!runId,
  });
}

// ── POST /calibration/train ──────────────────────────────────────────────────
interface TrainModelPayload {
  minSamplesRequired?: number;
  modelType?: string;
}

export function useRetrainCalibrationModel() {
  return useMutation<{ task_id: string; status: string; message: string }, Error, TrainModelPayload>({
    mutationFn: (payload) =>
      apiRequest<{ task_id: string; status: string; message: string }>("/api/v2/calibration/train", {
        method: "POST",
        body: JSON.stringify({
          min_samples_required: payload?.minSamplesRequired ?? 100,
          model_type: payload?.modelType ?? "logistic_regression",
        }),
      }),
  });
}

// ── GET /cohorts/my-benchmark ────────────────────────────────────────────────
export function useMyCohortBenchmark(userId: string | null) {
  return useQuery<BenchmarkReport>({
    queryKey: ["calibration", "cohorts", "benchmark", userId],
    queryFn: () => apiRequest<BenchmarkReport>("/api/v2/cohorts/my-benchmark"),
    enabled: !!userId,
    staleTime: STALE_TIME,
  });
}

// ── POST /cohorts/recluster ──────────────────────────────────────────────────
export function useForceReclusterCohorts(userId: string | null) {
  const queryClient = useQueryClient();

  return useMutation<{ job_id: string; status: string; message: string }, Error, void>({
    mutationFn: () =>
      apiRequest<{ job_id: string; status: string; message: string }>("/api/v2/cohorts/recluster", {
        method: "POST",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["calibration", "cohorts", "benchmark", userId] });
    },
  });
}

// ── POST /ml-platform/models/promote ─────────────────────────────────────────
interface PromoteModelPayload {
  modelName: string;
  versionTag: string;
  targetStage: string;
}

export function usePromoteModel() {
  return useMutation<ModelRegistrationInfo, Error, PromoteModelPayload>({
    mutationFn: (payload) =>
      apiRequest<ModelRegistrationInfo>("/api/v2/ml-platform/models/promote", {
        method: "POST",
        body: JSON.stringify({
          model_name: payload.modelName,
          version_tag: payload.versionTag,
          target_stage: payload.targetStage,
        }),
      }),
  });
}

// ── GET /ml-platform/models/compare ──────────────────────────────────────────
export function useCompareModels(candidateRunId: string | null, productionRunId: string | null) {
  return useQuery<any>({
    queryKey: ["calibration", "models", "compare", candidateRunId, productionRunId],
    queryFn: () =>
      apiRequest<any>(
        `/api/v2/ml-platform/models/compare?candidate_run_id=${candidateRunId}&production_run_id=${productionRunId}`
      ),
    enabled: !!candidateRunId && !!productionRunId,
  });
}
