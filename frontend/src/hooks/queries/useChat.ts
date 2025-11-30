import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";

// Types
export interface ChatConversation {
  id: string;
  title: string;
  created_at: string | null;
  updated_at: string | null;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string | null;
  metadata?: Record<string, unknown>;
}

export interface ConversationWithMessages {
  conversation: {
    id: string;
    title: string;
    created_at: string | null;
  };
  messages: ChatMessage[];
  total: number;
}

export interface ChatHistoryResponse {
  conversations: ChatConversation[];
  total: number;
}

// Cache times
const STALE_TIME = 2 * 60 * 1000; // 2 minutes
const CACHE_TIME = 10 * 60 * 1000; // 10 minutes

/**
 * Hook to fetch chat history (list of conversations)
 */
export function useChatHistory(userId: string | null, limit = 50) {
  return useQuery({
    queryKey: ["chat", "history", userId, limit],
    queryFn: () =>
      apiRequest<ChatHistoryResponse>(
        `/chat/history?user_id=${userId}&limit=${limit}`
      ),
    enabled: !!userId,
    staleTime: STALE_TIME,
    gcTime: CACHE_TIME,
  });
}

/**
 * Hook to fetch messages for a specific conversation
 */
export function useConversationMessages(
  conversationId: string | null,
  limit = 100
) {
  return useQuery({
    queryKey: ["chat", "conversation", conversationId, limit],
    queryFn: () =>
      apiRequest<ConversationWithMessages>(
        `/chat/history/${conversationId}?limit=${limit}`
      ),
    enabled: !!conversationId,
    staleTime: STALE_TIME,
    gcTime: CACHE_TIME,
  });
}

/**
 * Hook to create a new conversation
 */
export function useCreateConversation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      userId,
      title,
    }: {
      userId: string;
      title?: string;
    }) =>
      apiRequest<ChatConversation>(
        `/chat/history?user_id=${userId}${title ? `&title=${encodeURIComponent(title)}` : ""}`,
        { method: "POST" }
      ),
    onSuccess: (_, variables) => {
      // Invalidate chat history to refetch
      queryClient.invalidateQueries({
        queryKey: ["chat", "history", variables.userId],
      });
    },
  });
}

/**
 * Hook to delete a conversation
 */
export function useDeleteConversation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (conversationId: string) =>
      apiRequest<{ success: boolean; message: string }>(
        `/chat/history/${conversationId}`,
        { method: "DELETE" }
      ),
    onSuccess: () => {
      // Invalidate all chat history queries
      queryClient.invalidateQueries({
        queryKey: ["chat", "history"],
      });
    },
  });
}
