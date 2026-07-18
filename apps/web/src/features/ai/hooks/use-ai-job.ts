"use client";

import { useQuery } from "@tanstack/react-query";
import { normalizeApiError } from "@/lib/api/errors";
import { aiService } from "../services/ai.service";
import { ACTIVE_JOB_STATUSES, type AIJobResponse } from "../types";

export const AI_JOB_QUERY_KEY = (jobId: string) => ["ai", "jobs", "detail", jobId] as const;

export interface UseAIJobReturn {
  job: AIJobResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
  refetch: () => void;
}

/** Polls every 2s while the job is pending/running/retrying, then stops
 * automatically once it reaches a terminal status — components never need
 * to manage the polling lifecycle themselves. */
export function useAIJob(jobId: string | undefined): UseAIJobReturn {
  const result = useQuery({
    queryKey: AI_JOB_QUERY_KEY(jobId ?? ""),
    queryFn: ({ signal }) => aiService.getAIJob(jobId as string, signal),
    enabled: Boolean(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status && ACTIVE_JOB_STATUSES.has(status) ? 2000 : false;
    },
  });

  return {
    job: result.data,
    isLoading: result.isLoading,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
    refetch: () => void result.refetch(),
  };
}
