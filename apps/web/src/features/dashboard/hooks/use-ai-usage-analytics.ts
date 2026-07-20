"use client";

import { useQuery } from "@tanstack/react-query";
import { normalizeApiError } from "@/lib/api/errors";
import { dashboardService } from "../services/dashboard.service";
import type { AIUsageAnalyticsResponse } from "../types";

export interface UseAIUsageAnalyticsReturn {
  usage: AIUsageAnalyticsResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
  refetch: () => void;
}

export function useAIUsageAnalytics(): UseAIUsageAnalyticsReturn {
  const result = useQuery({
    queryKey: ["dashboard", "ai-usage"],
    queryFn: ({ signal }) => dashboardService.getAIUsageAnalytics(signal),
  });

  return {
    usage: result.data,
    isLoading: result.isLoading,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
    refetch: () => void result.refetch(),
  };
}
