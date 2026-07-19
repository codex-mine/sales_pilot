"use client";

import { useQuery } from "@tanstack/react-query";
import { normalizeApiError } from "@/lib/api/errors";
import { inboxService } from "../services/inbox.service";
import type { ConversationListItemResponse } from "../types";

export const LEAD_CONVERSATIONS_QUERY_KEY = (leadId: string) => ["inbox", "lead-conversations", leadId] as const;

export interface UseLeadConversationsReturn {
  conversations: ConversationListItemResponse[];
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
}

export function useLeadConversations(leadId: string | undefined): UseLeadConversationsReturn {
  const result = useQuery({
    queryKey: LEAD_CONVERSATIONS_QUERY_KEY(leadId ?? ""),
    queryFn: ({ signal }) => inboxService.getLeadConversations(leadId as string, signal),
    enabled: Boolean(leadId),
  });

  return {
    conversations: result.data ?? [],
    isLoading: result.isLoading,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
  };
}
