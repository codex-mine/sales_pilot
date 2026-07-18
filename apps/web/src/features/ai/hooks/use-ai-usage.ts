"use client";

import { useQuery } from "@tanstack/react-query";
import { normalizeApiError } from "@/lib/api/errors";
import { aiService } from "../services/ai.service";
import type { AIUsageResponse } from "../types";

export const AI_USAGE_QUERY_KEY = (days: number) => ["ai", "usage", days] as const;

export interface UseAIUsageReturn {
  usage: AIUsageResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
}

export function useAIUsage(days = 30): UseAIUsageReturn {
  const result = useQuery({
    queryKey: AI_USAGE_QUERY_KEY(days),
    queryFn: ({ signal }) => aiService.getAIUsage(days, signal),
  });

  return {
    usage: result.data,
    isLoading: result.isLoading,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
  };
}
