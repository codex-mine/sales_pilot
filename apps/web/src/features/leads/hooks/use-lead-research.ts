"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ACTIVE_JOB_STATUSES } from "@/features/ai/types";
import { normalizeApiError } from "@/lib/api/errors";
import { leadService } from "../services/lead.service";
import type { BulkResearchResponse, LeadResearchStatusResponse, ProspectAnalysisResponse } from "../types";
import { LEAD_QUERY_KEY } from "./use-lead";

export const LEAD_RESEARCH_QUERY_KEY = (leadId: string) => ["leads", "research", leadId] as const;
export const PROSPECT_ANALYSIS_QUERY_KEY = (leadId: string) => ["leads", "prospect-analysis", leadId] as const;

function isResearchInFlight(status: LeadResearchStatusResponse | undefined): boolean {
  if (!status) return false;
  if (status.company_job && ACTIVE_JOB_STATUSES.has(status.company_job.status)) return true;
  if (status.prospect_job && ACTIVE_JOB_STATUSES.has(status.prospect_job.status)) return true;
  // Company research finished but prospect analysis hasn't been created yet —
  // async orchestration is still chaining the two jobs together.
  if (status.lead_status === "researching" && !status.prospect_job) return true;
  return false;
}

export interface UseLeadResearchReturn {
  status: LeadResearchStatusResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
  isRunning: boolean;
  refetch: () => void;
}

/** Polls every 2s while company research and/or prospect analysis is still
 * in flight, stopping automatically once both reach a terminal status. */
export function useLeadResearch(leadId: string): UseLeadResearchReturn {
  const result = useQuery({
    queryKey: LEAD_RESEARCH_QUERY_KEY(leadId),
    queryFn: ({ signal }) => leadService.getLeadResearch(leadId, signal),
    enabled: Boolean(leadId),
    refetchInterval: (query) => (isResearchInFlight(query.state.data) ? 2000 : false),
  });

  return {
    status: result.data,
    isLoading: result.isLoading,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
    isRunning: isResearchInFlight(result.data),
    refetch: () => void result.refetch(),
  };
}

export interface UseTriggerLeadResearchReturn {
  triggerResearch: (args: { leadId: string; force?: boolean }) => Promise<LeadResearchStatusResponse>;
  isTriggering: boolean;
}

export function useTriggerLeadResearch(): UseTriggerLeadResearchReturn {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: ({ leadId, force }: { leadId: string; force?: boolean }) =>
      leadService.triggerLeadResearch(leadId, force),
    onSuccess: (status, { leadId }) => {
      queryClient.setQueryData(LEAD_RESEARCH_QUERY_KEY(leadId), status);
      void queryClient.invalidateQueries({ queryKey: LEAD_QUERY_KEY(leadId) });
      void queryClient.invalidateQueries({ queryKey: ["leads", "list"] });
      toast.success("Lead research started.");
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });

  return { triggerResearch: (args) => mutation.mutateAsync(args), isTriggering: mutation.isPending };
}

export interface UseProspectAnalysisReturn {
  analysis: ProspectAnalysisResponse | null | undefined;
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
  refetch: () => void;
}

export function useProspectAnalysis(leadId: string): UseProspectAnalysisReturn {
  const result = useQuery({
    queryKey: PROSPECT_ANALYSIS_QUERY_KEY(leadId),
    queryFn: ({ signal }) => leadService.getProspectAnalysis(leadId, signal),
    enabled: Boolean(leadId),
  });

  return {
    analysis: result.data,
    isLoading: result.isLoading,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
    refetch: () => void result.refetch(),
  };
}

export interface UseBulkTriggerResearchReturn {
  bulkTriggerResearch: (leadIds: string[]) => Promise<BulkResearchResponse>;
  isTriggering: boolean;
}

export function useBulkTriggerResearch(): UseBulkTriggerResearchReturn {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (leadIds: string[]) => leadService.bulkTriggerResearch({ lead_ids: leadIds }),
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: ["leads", "list"] });
      if (result.errors.length > 0) {
        toast.warning(`Research queued for ${result.queued_count} of ${result.requested_count} leads.`);
      } else {
        toast.success(
          `Research queued for ${result.queued_count} lead${result.queued_count === 1 ? "" : "s"}.`,
        );
      }
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });

  return { bulkTriggerResearch: (leadIds) => mutation.mutateAsync(leadIds), isTriggering: mutation.isPending };
}
