"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { normalizeApiError } from "@/lib/api/errors";
import { inboxService } from "../services/inbox.service";
import type { MessageResponse } from "../types";
import { CONVERSATION_QUERY_KEY } from "./use-conversation";

export const MESSAGE_QUERY_KEY = (messageId: string) => ["inbox", "message", messageId] as const;

export interface UseMessageReturn {
  message: MessageResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
}

export function useMessage(messageId: string | undefined): UseMessageReturn {
  const result = useQuery({
    queryKey: MESSAGE_QUERY_KEY(messageId ?? ""),
    queryFn: ({ signal }) => inboxService.getMessage(messageId as string, signal),
    enabled: Boolean(messageId),
  });

  return {
    message: result.data,
    isLoading: result.isLoading,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
  };
}

export interface UseReclassifyMessageReturn {
  reclassifyMessage: (args: { messageId: string; classification: string }) => Promise<MessageResponse>;
  isReclassifying: boolean;
}

export function useReclassifyMessage(): UseReclassifyMessageReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ messageId, classification }: { messageId: string; classification: string }) =>
      inboxService.reclassifyMessage(messageId, classification),
    onSuccess: (message) => {
      queryClient.setQueryData(MESSAGE_QUERY_KEY(message.id), message);
      void queryClient.invalidateQueries({ queryKey: CONVERSATION_QUERY_KEY(message.conversation_id) });
      void queryClient.invalidateQueries({ queryKey: ["inbox", "conversations"] });
      void queryClient.invalidateQueries({ queryKey: ["leads", "detail", message.lead_id] });
      toast.success("Message reclassified.");
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });
  return { reclassifyMessage: (args) => mutation.mutateAsync(args), isReclassifying: mutation.isPending };
}
