"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { normalizeApiError } from "@/lib/api/errors";
import { emailSenderService } from "../services/email-sender.service";
import type { EmailSenderConnectRequest, EmailSenderStatusResponse } from "../types";

export const EMAIL_SENDER_SETTINGS_QUERY_KEY = ["email-sender", "settings"] as const;

export interface UseEmailSenderSettingsReturn {
  settings: EmailSenderStatusResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
  refetch: () => void;
}

export function useEmailSenderSettings(): UseEmailSenderSettingsReturn {
  const result = useQuery({
    queryKey: EMAIL_SENDER_SETTINGS_QUERY_KEY,
    queryFn: ({ signal }) => emailSenderService.getEmailSenderSettings(signal),
  });

  return {
    settings: result.data,
    isLoading: result.isLoading,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
    refetch: () => void result.refetch(),
  };
}

export interface UseConnectEmailSenderReturn {
  connect: (payload: EmailSenderConnectRequest) => Promise<EmailSenderStatusResponse>;
  isConnecting: boolean;
}

export function useConnectEmailSender(): UseConnectEmailSenderReturn {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (payload: EmailSenderConnectRequest) => emailSenderService.connectEmailSender(payload),
    onSuccess: (settings) => {
      queryClient.setQueryData(EMAIL_SENDER_SETTINGS_QUERY_KEY, settings);
      toast.success("Sending mailbox connected.");
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });

  return { connect: (payload) => mutation.mutateAsync(payload), isConnecting: mutation.isPending };
}

export interface UseDisconnectEmailSenderReturn {
  disconnect: (integrationId: string) => Promise<void>;
  isDisconnecting: boolean;
}

export function useDisconnectEmailSender(): UseDisconnectEmailSenderReturn {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (integrationId: string) => emailSenderService.disconnectEmailSender(integrationId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: EMAIL_SENDER_SETTINGS_QUERY_KEY });
      toast.success("Sending mailbox disconnected.");
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });

  return { disconnect: (integrationId) => mutation.mutateAsync(integrationId), isDisconnecting: mutation.isPending };
}
