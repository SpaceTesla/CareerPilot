import { useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";
import {
  FeedbackItemType,
  FeedbackResponse,
  FeedbackValue,
  RecommendationFeedback,
} from "@/types/analysis";

const STALE_TIME = 5 * 60 * 1000; // 5 minutes

// ── List feedback  ──────────────────────────────────────────────────────────

export function useFeedback(
  userId: string | null,
  itemType?: FeedbackItemType
) {
  const queryKey = ["feedback", userId, itemType ?? "all"];

  const query = useQuery<FeedbackResponse>({
    queryKey,
    queryFn: () => {
      const base = `/feedback?user_id=${userId}`;
      const qs = itemType ? `${base}&item_type=${itemType}` : base;
      return apiRequest<FeedbackResponse>(qs);
    },
    enabled: !!userId,
    staleTime: STALE_TIME,
  });

  /** Quick O(1) lookup: itemIdentifier → FeedbackValue */
  const feedbackMap = useMemo<Map<string, FeedbackValue>>(() => {
    const map = new Map<string, FeedbackValue>();
    if (query.data?.feedback) {
      for (const item of query.data.feedback) {
        map.set(item.item_identifier, item.feedback);
      }
    }
    return map;
  }, [query.data]);

  return { ...query, feedbackMap };
}

// ── Submit / upsert feedback ───────────────────────────────────────────────

interface SubmitFeedbackPayload {
  user_id: string;
  item_type: FeedbackItemType;
  item_identifier: string;
  feedback: FeedbackValue;
}

export function useSubmitFeedback() {
  const queryClient = useQueryClient();

  return useMutation<RecommendationFeedback, Error, SubmitFeedbackPayload>({
    mutationFn: (payload) =>
      apiRequest<RecommendationFeedback>("/feedback", {
        method: "POST",
        body: JSON.stringify(payload),
        headers: { "Content-Type": "application/json" },
      }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["feedback", variables.user_id],
      });
    },
  });
}

// ── Delete / toggle off feedback ───────────────────────────────────────────

interface DeleteFeedbackPayload {
  user_id: string;
  item_type: FeedbackItemType;
  item_identifier: string;
}

export function useDeleteFeedback() {
  const queryClient = useQueryClient();

  return useMutation<{ deleted: boolean }, Error, DeleteFeedbackPayload>({
    mutationFn: ({ user_id, item_type, item_identifier }) =>
      apiRequest<{ deleted: boolean }>(
        `/feedback?user_id=${user_id}&item_type=${item_type}&item_identifier=${encodeURIComponent(item_identifier)}`,
        { method: "DELETE" }
      ),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["feedback", variables.user_id],
      });
    },
  });
}
