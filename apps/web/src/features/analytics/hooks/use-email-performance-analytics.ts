"use client";

import { useQuery } from "@tanstack/react-query";
import { normalizeApiError } from "@/lib/api/errors";
import { analyticsService } from "../services/analytics.service";
import type { EmailPerformanceAnalyticsResponse, EmailPerformanceFilters } from "../types";

export const EMAIL_PERFORMANCE_ANALYTICS_QUERY_KEY = (filters: EmailPerformanceFilters) =>
  ["analytics", "email-performance", filters] as const;

export interface UseEmailPerformanceAnalyticsReturn {
  analytics: EmailPerformanceAnalyticsResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
  refetch: () => void;
}

export function useEmailPerformanceAnalytics(
  filters: EmailPerformanceFilters = {},
): UseEmailPerformanceAnalyticsReturn {
  const result = useQuery({
    queryKey: EMAIL_PERFORMANCE_ANALYTICS_QUERY_KEY(filters),
    queryFn: ({ signal }) => analyticsService.getEmailPerformanceAnalytics(filters, signal),
    placeholderData: (previous) => previous,
  });

  return {
    analytics: result.data,
    isLoading: result.isLoading,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
    refetch: () => void result.refetch(),
  };
}
