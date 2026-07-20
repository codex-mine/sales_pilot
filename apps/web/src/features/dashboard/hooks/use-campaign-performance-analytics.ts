"use client";

import { useQuery } from "@tanstack/react-query";
import { normalizeApiError } from "@/lib/api/errors";
import { dashboardService } from "../services/dashboard.service";
import type { CampaignPerformanceResponse } from "../types";

export interface UseCampaignPerformanceAnalyticsReturn {
  performance: CampaignPerformanceResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
  refetch: () => void;
}

export function useCampaignPerformanceAnalytics(limit = 10): UseCampaignPerformanceAnalyticsReturn {
  const result = useQuery({
    queryKey: ["dashboard", "campaign-performance", limit],
    queryFn: ({ signal }) => dashboardService.getCampaignPerformanceAnalytics(limit, signal),
  });

  return {
    performance: result.data,
    isLoading: result.isLoading,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
    refetch: () => void result.refetch(),
  };
}
