import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { apiRequest } from "@/lib/api";
import { getCachedData, setCachedData } from "@/lib/query-persister";
import type {
  UserDigestBrief,
  UserDigestDetail,
  StrategyReviewBrief,
  StrategyReviewDetail,
} from "@/types/analysis";

const STALE_TIME = 5 * 60 * 1000; // 5 minutes
const CACHE_TIME = 30 * 60 * 1000; // 30 minutes

export function useUserDigests(userId: string | null) {
  const queryKey = ["strategy", "digests", userId];
  const cachedData = getCachedData<{ digests: UserDigestBrief[] }>(queryKey);

  const query = useQuery({
    queryKey,
    queryFn: () => apiRequest<{ digests: UserDigestBrief[] }>("/api/v2/strategy/digests"),
    enabled: !!userId,
    staleTime: STALE_TIME,
    gcTime: CACHE_TIME,
    initialData: cachedData,
  });

  useEffect(() => {
    if (query.isSuccess && query.data) {
      setCachedData(queryKey, query.data);
    }
  }, [query.isSuccess, query.data]);

  return query;
}

export function useUserDigestDetail(digestId: string | null) {
  const queryKey = ["strategy", "digests", "detail", digestId];
  const cachedData = getCachedData<UserDigestDetail>(queryKey);

  const query = useQuery({
    queryKey,
    queryFn: () => apiRequest<UserDigestDetail>(`/api/v2/strategy/digests/${digestId}`),
    enabled: !!digestId,
    staleTime: STALE_TIME,
    gcTime: CACHE_TIME,
    initialData: cachedData,
  });

  useEffect(() => {
    if (query.isSuccess && query.data) {
      setCachedData(queryKey, query.data);
    }
  }, [query.isSuccess, query.data]);

  return query;
}

export function useStrategyReviews(userId: string | null) {
  const queryKey = ["strategy", "reviews", userId];
  const cachedData = getCachedData<{ reviews: StrategyReviewBrief[] }>(queryKey);

  const query = useQuery({
    queryKey,
    queryFn: () => apiRequest<{ reviews: StrategyReviewBrief[] }>("/api/v2/strategy/reviews"),
    enabled: !!userId,
    staleTime: STALE_TIME,
    gcTime: CACHE_TIME,
    initialData: cachedData,
  });

  useEffect(() => {
    if (query.isSuccess && query.data) {
      setCachedData(queryKey, query.data);
    }
  }, [query.isSuccess, query.data]);

  return query;
}

export function useStrategyReviewDetail(reviewId: string | null) {
  const queryKey = ["strategy", "reviews", "detail", reviewId];
  const cachedData = getCachedData<StrategyReviewDetail>(queryKey);

  const query = useQuery({
    queryKey,
    queryFn: () => apiRequest<StrategyReviewDetail>(`/api/v2/strategy/reviews/${reviewId}`),
    enabled: !!reviewId,
    staleTime: STALE_TIME,
    gcTime: CACHE_TIME,
    initialData: cachedData,
  });

  useEffect(() => {
    if (query.isSuccess && query.data) {
      setCachedData(queryKey, query.data);
    }
  }, [query.isSuccess, query.data]);

  return query;
}

export function useCompleteReview() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      reviewId,
      feedbackText,
      acceptActionItems,
    }: {
      reviewId: string;
      feedbackText: string;
      acceptActionItems: boolean;
    }) =>
      apiRequest<{ id: string; status: string; completed_at: string }>(
        `/api/v2/strategy/reviews/${reviewId}/complete`,
        {
          method: "POST",
          body: JSON.stringify({
            feedback_text: feedbackText,
            accept_action_items: acceptActionItems,
          }),
        }
      ),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["strategy", "reviews"] });
      queryClient.invalidateQueries({
        queryKey: ["strategy", "reviews", "detail", variables.reviewId],
      });
    },
  });
}

export function useUpdateActionItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      itemId,
      reviewId,
      status,
    }: {
      itemId: string;
      reviewId: string;
      status: "TODO" | "COMPLETED" | "CANCELLED";
    }) =>
      apiRequest<{ id: string; status: string; completed_at: string | null }>(
        `/api/v2/strategy/reviews/action-items/${itemId}`,
        {
          method: "PATCH",
          body: JSON.stringify({ status }),
        }
      ),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["strategy", "reviews", "detail", variables.reviewId],
      });
    },
  });
}

export function useUpdatePreferences() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: {
      weekly_digest_enabled?: boolean;
      digest_delivery_day?: number;
      digest_delivery_hour?: number;
    }) =>
      apiRequest<unknown>("/api/v2/profile/preferences", {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["profile", "preferences"] });
    },
  });
}
