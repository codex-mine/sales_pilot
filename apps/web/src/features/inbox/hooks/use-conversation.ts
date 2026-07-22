"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { normalizeApiError } from "@/lib/api/errors";
import { inboxService } from "../services/inbox.service";
import type { ConversationDetailResponse } from "../types";

export const CONVERSATION_QUERY_KEY = (conversationId: string) => ["inbox", "conversation", conversationId] as const;

export interface UseConversationReturn {
  conversation: ConversationDetailResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
  refetch: () => void;
}

/** The most recent inbound message still has `reply_classification: null` —
 * AI classification (module 09, now module 13's `reply_agent` graph) is
 * still in flight for it. There's no job id surfaced on `Message` to drive
 * `AgentStepTimeline` here, so this just tells the view to keep polling and
 * show a lightweight "Classifying reply…" indicator instead of the full
 * step-by-step timeline Research/Email Generation get. */
function hasPendingClassification(conversation: ConversationDetailResponse | undefined): boolean {
  const latestInbound = [...(conversation?.items ?? [])].reverse().find((item) => item.direction === "inbound");
  return Boolean(latestInbound && latestInbound.reply_classification === null);
}

export function useConversation(conversationId: string | undefined): UseConversationReturn {
  const result = useQuery({
    queryKey: CONVERSATION_QUERY_KEY(conversationId ?? ""),
    queryFn: ({ signal }) => inboxService.getConversation(conversationId as string, signal),
    enabled: Boolean(conversationId),
    refetchInterval: (query) => (hasPendingClassification(query.state.data) ? 2000 : false),
  });

  return {
    conversation: result.data,
    isLoading: result.isLoading,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
    refetch: () => void result.refetch(),
  };
}

export interface UseMarkConversationReadReturn {
  markConversationRead: (args: { conversationId: string; isRead: boolean }) => Promise<ConversationDetailResponse>;
  isMarking: boolean;
}

/** No success toast — this fires automatically on thread open, not from an explicit user action. */
export function useMarkConversationRead(): UseMarkConversationReadReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ conversationId, isRead }: { conversationId: string; isRead: boolean }) =>
      inboxService.markConversationRead(conversationId, isRead),
    onSuccess: (conversation) => {
      queryClient.setQueryData(CONVERSATION_QUERY_KEY(conversation.id), conversation);
      void queryClient.invalidateQueries({ queryKey: ["inbox", "conversations"] });
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });
  return { markConversationRead: (args) => mutation.mutateAsync(args), isMarking: mutation.isPending };
}
