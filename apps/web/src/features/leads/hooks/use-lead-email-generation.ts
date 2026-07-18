"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { AI_JOB_QUERY_KEY } from "@/features/ai/hooks/use-ai-job";
import type { AIJobResponse, AIOutputResponse } from "@/features/ai/types";
import { normalizeApiError } from "@/lib/api/errors";
import { leadService } from "../services/lead.service";
import type {
  ApproveEmailVariantRequest,
  BulkEmailGenerationResponse,
  BulkLeadEmailGenerationRequest,
  EmailResponse,
  GenerateEmailRequest,
  RegenerateEmailRequest,
} from "../types";
import { LEAD_QUERY_KEY } from "./use-lead";

export const LEAD_EMAIL_DRAFTS_QUERY_KEY = (leadId: string) => ["leads", "email-drafts", leadId] as const;

export interface UseLeadEmailDraftsReturn {
  drafts: EmailResponse[];
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
  refetch: () => void;
}

/** DRAFT `Email` rows for a lead — the approved, ready-to-send outputs of
 * this module. Pending (unapproved) variants live on the AIJob itself
 * (`job.outputs`, read via `useAIJob`), not here. */
export function useLeadEmailDrafts(leadId: string): UseLeadEmailDraftsReturn {
  const result = useQuery({
    queryKey: LEAD_EMAIL_DRAFTS_QUERY_KEY(leadId),
    queryFn: ({ signal }) => leadService.getLeadEmailDrafts(leadId, signal),
    enabled: Boolean(leadId),
  });

  return {
    drafts: result.data ?? [],
    isLoading: result.isLoading,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
    refetch: () => void result.refetch(),
  };
}

export interface UseGenerateLeadEmailReturn {
  generateEmail: (args: { leadId: string; payload: GenerateEmailRequest }) => Promise<AIJobResponse>;
  isGenerating: boolean;
}

export function useGenerateLeadEmail(): UseGenerateLeadEmailReturn {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: ({ leadId, payload }: { leadId: string; payload: GenerateEmailRequest }) =>
      leadService.generateLeadEmail(leadId, payload),
    onSuccess: (job) => {
      queryClient.setQueryData(AI_JOB_QUERY_KEY(job.id), job);
      toast.success("Email generation started.");
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });

  return { generateEmail: (args) => mutation.mutateAsync(args), isGenerating: mutation.isPending };
}

export interface UseRegenerateEmailVariantReturn {
  regenerate: (args: { leadId: string; payload: RegenerateEmailRequest }) => Promise<AIJobResponse>;
  isRegenerating: boolean;
}

export function useRegenerateEmailVariant(): UseRegenerateEmailVariantReturn {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: ({ leadId, payload }: { leadId: string; payload: RegenerateEmailRequest }) =>
      leadService.regenerateLeadEmail(leadId, payload),
    onSuccess: (job) => {
      queryClient.setQueryData(AI_JOB_QUERY_KEY(job.id), job);
      toast.success("Regenerating with your feedback…");
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });

  return { regenerate: (args) => mutation.mutateAsync(args), isRegenerating: mutation.isPending };
}

export interface UseApproveEmailVariantReturn {
  approve: (args: { outputId: string; leadId: string; payload: ApproveEmailVariantRequest }) => Promise<EmailResponse>;
  isApproving: boolean;
}

export function useApproveEmailVariant(): UseApproveEmailVariantReturn {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: ({ outputId, payload }: { outputId: string; leadId: string; payload: ApproveEmailVariantRequest }) =>
      leadService.approveEmailVariant(outputId, payload),
    onSuccess: (_email, { leadId }) => {
      void queryClient.invalidateQueries({ queryKey: LEAD_EMAIL_DRAFTS_QUERY_KEY(leadId) });
      void queryClient.invalidateQueries({ queryKey: LEAD_QUERY_KEY(leadId) });
      toast.success("Email approved as a draft.");
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });

  return { approve: (args) => mutation.mutateAsync(args), isApproving: mutation.isPending };
}

export interface UseRejectEmailVariantReturn {
  reject: (args: { outputId: string; jobId: string }) => Promise<AIOutputResponse>;
  isRejecting: boolean;
}

export function useRejectEmailVariant(): UseRejectEmailVariantReturn {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: ({ outputId }: { outputId: string; jobId: string }) => leadService.rejectEmailVariant(outputId),
    onSuccess: (_output, { jobId }) => {
      void queryClient.invalidateQueries({ queryKey: AI_JOB_QUERY_KEY(jobId) });
      toast.success("Variant rejected.");
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });

  return { reject: (args) => mutation.mutateAsync(args), isRejecting: mutation.isPending };
}

export interface UseBulkGenerateEmailsReturn {
  bulkGenerate: (payload: BulkLeadEmailGenerationRequest) => Promise<BulkEmailGenerationResponse>;
  isGenerating: boolean;
}

export function useBulkGenerateEmails(): UseBulkGenerateEmailsReturn {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (payload: BulkLeadEmailGenerationRequest) => leadService.bulkGenerateEmails(payload),
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: ["leads", "list"] });
      if (result.errors.length > 0) {
        toast.warning(
          `Email generation queued for ${result.queued_count} of ${result.requested_count} leads. ` +
            "Review each lead's Outreach tab once generation completes.",
        );
      } else {
        toast.success(
          `Email generation queued for ${result.queued_count} lead${result.queued_count === 1 ? "" : "s"}. ` +
            "Review each lead's Outreach tab once generation completes.",
        );
      }
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });

  return { bulkGenerate: (payload) => mutation.mutateAsync(payload), isGenerating: mutation.isPending };
}
