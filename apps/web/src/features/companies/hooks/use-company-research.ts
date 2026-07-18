"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { AI_JOB_QUERY_KEY } from "@/features/ai/hooks/use-ai-job";
import type { AIJobListItemResponse, AIJobResponse } from "@/features/ai/types";
import { normalizeApiError } from "@/lib/api/errors";
import { companyService } from "../services/company.service";
import type { CompanyResearchResponse } from "../types";

export const COMPANY_RESEARCH_QUERY_KEY = (companyId: string) =>
  ["companies", "research", companyId] as const;
export const COMPANY_RESEARCH_HISTORY_QUERY_KEY = (companyId: string) =>
  ["companies", "research-history", companyId] as const;

export interface UseCompanyResearchReturn {
  research: CompanyResearchResponse | null | undefined;
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
  refetch: () => void;
}

/** The current (latest) research profile for a company — null once loaded if
 * research has never run. Re-research overwrites this row; full history is
 * `useCompanyResearchHistory`. */
export function useCompanyResearch(companyId: string): UseCompanyResearchReturn {
  const result = useQuery({
    queryKey: COMPANY_RESEARCH_QUERY_KEY(companyId),
    queryFn: ({ signal }) => companyService.getCompanyResearch(companyId, signal),
    enabled: Boolean(companyId),
  });

  return {
    research: result.data,
    isLoading: result.isLoading,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
    refetch: () => void result.refetch(),
  };
}

export interface UseTriggerCompanyResearchReturn {
  triggerResearch: (args: { companyId: string; force?: boolean }) => Promise<AIJobResponse>;
  isTriggering: boolean;
}

export function useTriggerCompanyResearch(): UseTriggerCompanyResearchReturn {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: ({ companyId, force }: { companyId: string; force?: boolean }) =>
      companyService.triggerCompanyResearch(companyId, force),
    onSuccess: (job, { companyId }) => {
      queryClient.setQueryData(AI_JOB_QUERY_KEY(job.id), job);
      void queryClient.invalidateQueries({ queryKey: COMPANY_RESEARCH_HISTORY_QUERY_KEY(companyId) });
      toast.success("Company research started.");
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });

  return { triggerResearch: (args) => mutation.mutateAsync(args), isTriggering: mutation.isPending };
}

export interface UseCompanyResearchHistoryReturn {
  jobs: AIJobListItemResponse[];
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
}

export function useCompanyResearchHistory(companyId: string): UseCompanyResearchHistoryReturn {
  const result = useQuery({
    queryKey: COMPANY_RESEARCH_HISTORY_QUERY_KEY(companyId),
    queryFn: async () => (await companyService.getCompanyResearchHistory(companyId)).jobs,
    enabled: Boolean(companyId),
  });

  return {
    jobs: result.data ?? [],
    isLoading: result.isLoading,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
  };
}
