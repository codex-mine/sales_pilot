"use client";

import { useQuery } from "@tanstack/react-query";
import { normalizeApiError } from "@/lib/api/errors";
import { inboxService } from "../services/inbox.service";
import type { ConversationListItemResponse, ConversationsQuery, PaginationMeta } from "../types";

export const CONVERSATIONS_QUERY_KEY = (query: ConversationsQuery) => ["inbox", "conversations", query] as const;

export interface UseConversationsReturn {
  conversations: ConversationListItemResponse[];
  meta: PaginationMeta;
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
  refetch: () => void;
}

export function useConversations(query: ConversationsQuery = {}): UseConversationsReturn {
  const result = useQuery({
    queryKey: CONVERSATIONS_QUERY_KEY(query),
    queryFn: ({ signal }) => inboxService.getConversations(query, signal),
    placeholderData: (previous) => previous,
  });

  return {
    conversations: result.data?.conversations ?? [],
    meta: result.data?.meta ?? { page: 1, page_size: 25, total: 0 },
    isLoading: result.isLoading,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
    refetch: () => void result.refetch(),
  };
}
