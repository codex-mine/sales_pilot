"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { normalizeApiError } from "@/lib/api/errors";
import { leadService } from "../services/lead.service";
import type {
  BulkSendRequest,
  BulkSendResponse,
  EmailPreviewResponse,
  EmailResponse,
  OutboxEmailResponse,
  PaginationMeta,
  ScheduleEmailRequest,
} from "../types";
import { LEAD_EMAIL_DRAFTS_QUERY_KEY } from "./use-lead-email-generation";
import { LEAD_QUERY_KEY } from "./use-lead";

export const EMAIL_OUTBOX_QUERY_KEY = (query: Record<string, unknown>) => ["emails", "outbox", query] as const;
export const EMAIL_PREVIEW_QUERY_KEY = (emailId: string) => ["emails", "preview", emailId] as const;

function invalidateLeadEmailQueries(queryClient: ReturnType<typeof useQueryClient>, leadId: string): void {
  void queryClient.invalidateQueries({ queryKey: LEAD_EMAIL_DRAFTS_QUERY_KEY(leadId) });
  void queryClient.invalidateQueries({ queryKey: LEAD_QUERY_KEY(leadId) });
  void queryClient.invalidateQueries({ queryKey: ["emails", "outbox"] });
}

export interface UseSendEmailReturn {
  sendEmail: (args: { leadId: string; emailId: string }) => Promise<EmailResponse>;
  isSending: boolean;
}

export function useSendEmail(): UseSendEmailReturn {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: ({ leadId, emailId }: { leadId: string; emailId: string }) =>
      leadService.sendLeadEmail(leadId, emailId),
    onSuccess: (email, { leadId }) => {
      invalidateLeadEmailQueries(queryClient, leadId);
      toast.success(email.current_status === "sent" ? "Email sent." : "Send deferred — daily limit reached.");
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });

  return { sendEmail: (args) => mutation.mutateAsync(args), isSending: mutation.isPending };
}

export interface UseScheduleEmailReturn {
  scheduleEmail: (args: { leadId: string; emailId: string; payload: ScheduleEmailRequest }) => Promise<EmailResponse>;
  isScheduling: boolean;
}

export function useScheduleEmail(): UseScheduleEmailReturn {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: ({ leadId, emailId, payload }: { leadId: string; emailId: string; payload: ScheduleEmailRequest }) =>
      leadService.scheduleLeadEmail(leadId, emailId, payload),
    onSuccess: (_email, { leadId }) => {
      invalidateLeadEmailQueries(queryClient, leadId);
      toast.success("Email scheduled.");
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });

  return { scheduleEmail: (args) => mutation.mutateAsync(args), isScheduling: mutation.isPending };
}

export interface UseCancelScheduledEmailReturn {
  cancelEmail: (args: { leadId: string; emailId: string }) => Promise<EmailResponse>;
  isCancelling: boolean;
}

export function useCancelScheduledEmail(): UseCancelScheduledEmailReturn {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: ({ leadId, emailId }: { leadId: string; emailId: string }) =>
      leadService.cancelLeadEmail(leadId, emailId),
    onSuccess: (_email, { leadId }) => {
      invalidateLeadEmailQueries(queryClient, leadId);
      toast.success("Scheduled send cancelled.");
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });

  return { cancelEmail: (args) => mutation.mutateAsync(args), isCancelling: mutation.isPending };
}

export interface UseEmailPreviewReturn {
  preview: EmailPreviewResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
}

export function useEmailPreview(emailId: string | undefined): UseEmailPreviewReturn {
  const result = useQuery({
    queryKey: EMAIL_PREVIEW_QUERY_KEY(emailId ?? ""),
    queryFn: ({ signal }) => leadService.getEmailPreview(emailId as string, signal),
    enabled: Boolean(emailId),
  });

  return {
    preview: result.data,
    isLoading: result.isLoading,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
  };
}

export interface UseEmailOutboxReturn {
  emails: OutboxEmailResponse[];
  meta: PaginationMeta;
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
  refetch: () => void;
}

export function useEmailOutbox(query: {
  status?: string[];
  search?: string;
  page?: number;
  page_size?: number;
} = {}): UseEmailOutboxReturn {
  const result = useQuery({
    queryKey: EMAIL_OUTBOX_QUERY_KEY(query),
    queryFn: ({ signal }) => leadService.getEmailOutbox(query, signal),
    placeholderData: (previous) => previous,
    // Poll while anything in the current page is mid-flight, so a bulk send
    // or the scheduler firing shows up without a manual refresh.
    refetchInterval: (q) => (q.state.data?.emails.some((e) => e.current_status === "sending") ? 2000 : false),
  });

  return {
    emails: result.data?.emails ?? [],
    meta: result.data?.meta ?? { page: 1, page_size: 25, total: 0 },
    isLoading: result.isLoading,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
    refetch: () => void result.refetch(),
  };
}

export interface UseBulkSendEmailsReturn {
  bulkSend: (payload: BulkSendRequest) => Promise<BulkSendResponse>;
  isSending: boolean;
}

export function useBulkSendEmails(): UseBulkSendEmailsReturn {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (payload: BulkSendRequest) => leadService.bulkSendEmails(payload),
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: ["leads", "list"] });
      void queryClient.invalidateQueries({ queryKey: ["emails", "outbox"] });
      if (result.failed_count > 0) {
        toast.warning(`${result.success_count} sent, ${result.failed_count} failed.`);
      } else {
        toast.success(`${result.success_count} email${result.success_count === 1 ? "" : "s"} sent.`);
      }
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });

  return { bulkSend: (payload) => mutation.mutateAsync(payload), isSending: mutation.isPending };
}
