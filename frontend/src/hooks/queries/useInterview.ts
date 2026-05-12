import { useQuery, useMutation } from "@tanstack/react-query";
import { useEffect } from "react";
import { apiRequest } from "@/lib/api";
import { getCachedData, setCachedData } from "@/lib/query-persister";
import type { InterviewPrep, InterviewQuestions } from "@/types/analysis";

// Cache times for interview data - longer since questions don't change often
const STALE_TIME = 15 * 60 * 1000; // 15 minutes
const CACHE_TIME = 60 * 60 * 1000; // 60 minutes

export function useInterviewPrep(userId: string | null, role?: string) {
  const queryKey = ["interview", "prep", userId, role];
  const cachedData = getCachedData<InterviewPrep>(queryKey);
  
  const query = useQuery({
    queryKey,
    queryFn: () => {
      let endpoint = `/interview/prep?user_id=${userId}`;
      if (role) endpoint += `&role=${encodeURIComponent(role)}`;
      return apiRequest<InterviewPrep>(endpoint);
    },
    enabled: !!userId,
    staleTime: STALE_TIME,
    gcTime: CACHE_TIME,
    initialData: cachedData,
    initialDataUpdatedAt: cachedData ? Date.now() - 60000 : undefined,
  });
  
  useEffect(() => {
    if (query.isSuccess && query.data) {
      setCachedData(queryKey, query.data);
    }
  }, [query.isSuccess, query.data]);
  
  return query;
}

export function useInterviewQuestions(userId: string | null) {
  const queryKey = ["interview", "questions", userId];
  const cachedData = getCachedData<InterviewQuestions>(queryKey);
  
  const query = useQuery({
    queryKey,
    queryFn: () =>
      apiRequest<InterviewQuestions>(
        `/interview/questions?user_id=${userId}`
      ),
    enabled: !!userId,
    staleTime: STALE_TIME,
    gcTime: CACHE_TIME,
    initialData: cachedData,
    initialDataUpdatedAt: cachedData ? Date.now() - 60000 : undefined,
  });
  
  useEffect(() => {
    if (query.isSuccess && query.data) {
      setCachedData(queryKey, query.data);
    }
  }, [query.isSuccess, query.data]);
  
  return query;
}

interface QuestionsByCategoryResponse {
  questions: string;
  category: string;
  categories: string[];
}

export function useInterviewQuestionsByCategory(userId: string | null, category?: string) {
  const queryKey = ["interview", "questions", "category", userId, category];
  const cachedData = getCachedData<QuestionsByCategoryResponse>(queryKey);
  
  const query = useQuery({
    queryKey,
    queryFn: () => {
      let endpoint = `/interview/questions-by-category?user_id=${userId}`;
      if (category) endpoint += `&category=${encodeURIComponent(category)}`;
      return apiRequest<QuestionsByCategoryResponse>(endpoint);
    },
    enabled: !!userId,
    staleTime: STALE_TIME,
    gcTime: CACHE_TIME,
    initialData: cachedData,
    initialDataUpdatedAt: cachedData ? Date.now() - 60000 : undefined,
  });
  
  useEffect(() => {
    if (query.isSuccess && query.data) {
      setCachedData(queryKey, query.data);
    }
  }, [query.isSuccess, query.data]);
  
  return query;
}

export function useEvaluateAnswer() {
  return useMutation({
    mutationFn: async ({
      userId,
      question,
      answer,
      questionType,
    }: {
      userId: string;
      question: string;
      answer: string;
      questionType?: string;
    }) => {
      return apiRequest<{
        question: string;
        question_type: string;
        feedback: {
          strengths: string[];
          improvements: string[];
          suggestions: string[];
          scores: {
            clarity: number;
            relevance: number;
            examples: number;
            technical: number;
          };
          sample_answer?: string;
        };
        overall_score: number;
      }>(`/interview/evaluate-answer`, {
        method: "POST",
        body: JSON.stringify({
          user_id: userId,
          question,
          answer,
          question_type: questionType,
        }),
      });
    },
  });
}

