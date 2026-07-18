"use client";

import { useQuery } from "@tanstack/react-query";
import { normalizeApiError } from "@/lib/api/errors";
import { aiService } from "../services/ai.service";
import type { AIJobListItemResponse, AIJobsQuery, PaginationMeta } from "../types";

export const AI_JOBS_QUERY_KEY = (query: AIJobsQuery) => ["ai", "jobs", "list", query] as const;

export interface UseAIJobsReturn {
  jobs: AIJobListItemResponse[];
  meta: PaginationMeta;
  isLoading: boolean;
  isFetching: boolean;
  isError: boolean;
  errorMessage: string | null;
  refetch: () => void;
}

/** Server-side filter/pagination — pass the full query object as component state. */
export function useAIJobs(query: AIJobsQuery): UseAIJobsReturn {
  const result = useQuery({
    queryKey: AI_JOBS_QUERY_KEY(query),
    queryFn: ({ signal }) => aiService.getAIJobs(query, signal),
    placeholderData: (previous) => previous,
  });

  return {
    jobs: result.data?.jobs ?? [],
    meta: result.data?.meta ?? { page: query.page ?? 1, page_size: query.page_size ?? 25, total: 0 },
    isLoading: result.isLoading,
    isFetching: result.isFetching,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
    refetch: () => void result.refetch(),
  };
}
