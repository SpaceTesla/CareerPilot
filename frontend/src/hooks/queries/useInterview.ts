import { useQuery, useMutation } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";
import type { InterviewPrep, InterviewQuestions } from "@/types/analysis";

export function useInterviewPrep(userId: string | null, role?: string) {
  return useQuery({
    queryKey: ["interview", "prep", userId, role],
    queryFn: () => {
      let endpoint = `/interview/prep?user_id=${userId}`;
      if (role) endpoint += `&role=${encodeURIComponent(role)}`;
      return apiRequest<InterviewPrep>(endpoint);
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

export function useInterviewQuestionsByCategory(userId: string | null, category?: string) {
  return useQuery({
    queryKey: ["interview", "questions", "category", userId, category],
    queryFn: () => {
      let endpoint = `/interview/questions-by-category?user_id=${userId}`;
      if (category) endpoint += `&category=${encodeURIComponent(category)}`;
      return apiRequest<{ questions: string; category: string; categories: string[] }>(endpoint);
    },
    enabled: !!userId,
  });
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

