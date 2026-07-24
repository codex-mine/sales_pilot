"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { normalizeApiError } from "@/lib/api/errors";
import { emailSenderService } from "../services/email-sender.service";
import type {
  CreateSenderMailboxRequest,
  SenderMailboxResponse,
  TestSmtpConnectionRequest,
  UpdateSenderMailboxRequest,
} from "../types";

export const SENDER_MAILBOXES_QUERY_KEY = ["email-sender", "mailboxes"] as const;

export interface UseSenderMailboxesReturn {
  mailboxes: SenderMailboxResponse[];
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
  refetch: () => void;
}

export function useSenderMailboxes(): UseSenderMailboxesReturn {
  const result = useQuery({
    queryKey: SENDER_MAILBOXES_QUERY_KEY,
    queryFn: ({ signal }) => emailSenderService.getSenderMailboxes(signal),
  });

  return {
    mailboxes: result.data ?? [],
    isLoading: result.isLoading,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
    refetch: () => void result.refetch(),
  };
}

export interface UseTestSmtpConnectionReturn {
  testConnection: (payload: TestSmtpConnectionRequest) => Promise<void>;
  isTesting: boolean;
}

/** Standalone "Test Connection" probe for the mailbox form — separate from
 * create/update's own built-in test-before-save, so a user gets feedback
 * before committing to submit. */
export function useTestSmtpConnection(): UseTestSmtpConnectionReturn {
  const mutation = useMutation({
    mutationFn: (payload: TestSmtpConnectionRequest) => emailSenderService.testSmtpConnection(payload),
    onSuccess: () => toast.success("Connection succeeded."),
    onError: (error) => toast.error(normalizeApiError(error).message),
  });
  return { testConnection: (payload) => mutation.mutateAsync(payload), isTesting: mutation.isPending };
}

export interface UseCreateSenderMailboxReturn {
  createMailbox: (payload: CreateSenderMailboxRequest) => Promise<SenderMailboxResponse>;
  isCreating: boolean;
}

export function useCreateSenderMailbox(): UseCreateSenderMailboxReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (payload: CreateSenderMailboxRequest) => emailSenderService.createSenderMailbox(payload),
    onSuccess: () => {
      toast.success("Sender mailbox connected.");
      void queryClient.invalidateQueries({ queryKey: SENDER_MAILBOXES_QUERY_KEY });
    },
  });
  return { createMailbox: (payload) => mutation.mutateAsync(payload), isCreating: mutation.isPending };
}

export interface UseUpdateSenderMailboxReturn {
  updateMailbox: (args: { mailboxId: string; payload: UpdateSenderMailboxRequest }) => Promise<SenderMailboxResponse>;
  isUpdating: boolean;
}

export function useUpdateSenderMailbox(): UseUpdateSenderMailboxReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ mailboxId, payload }: { mailboxId: string; payload: UpdateSenderMailboxRequest }) =>
      emailSenderService.updateSenderMailbox(mailboxId, payload),
    onSuccess: () => {
      toast.success("Sender mailbox updated.");
      void queryClient.invalidateQueries({ queryKey: SENDER_MAILBOXES_QUERY_KEY });
    },
  });
  return { updateMailbox: (args) => mutation.mutateAsync(args), isUpdating: mutation.isPending };
}

export interface UseDeleteSenderMailboxReturn {
  deleteMailbox: (mailboxId: string) => Promise<void>;
  isDeleting: boolean;
}

export function useDeleteSenderMailbox(): UseDeleteSenderMailboxReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (mailboxId: string) => emailSenderService.deleteSenderMailbox(mailboxId),
    onSuccess: () => {
      toast.success("Sender mailbox deleted.");
      void queryClient.invalidateQueries({ queryKey: SENDER_MAILBOXES_QUERY_KEY });
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });
  return { deleteMailbox: (mailboxId) => mutation.mutateAsync(mailboxId), isDeleting: mutation.isPending };
}

export interface UseSetDefaultSenderMailboxReturn {
  setDefault: (mailboxId: string) => Promise<SenderMailboxResponse>;
  isSettingDefault: boolean;
}

export function useSetDefaultSenderMailbox(): UseSetDefaultSenderMailboxReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (mailboxId: string) => emailSenderService.setDefaultSenderMailbox(mailboxId),
    onSuccess: () => {
      toast.success("Default mailbox updated.");
      void queryClient.invalidateQueries({ queryKey: SENDER_MAILBOXES_QUERY_KEY });
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });
  return { setDefault: (mailboxId) => mutation.mutateAsync(mailboxId), isSettingDefault: mutation.isPending };
}
