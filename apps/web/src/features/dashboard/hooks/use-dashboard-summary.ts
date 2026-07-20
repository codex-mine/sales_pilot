"use client";

import { useQuery } from "@tanstack/react-query";
import { normalizeApiError } from "@/lib/api/errors";
import { dashboardService } from "../services/dashboard.service";
import type { DashboardSummaryResponse } from "../types";

export const DASHBOARD_SUMMARY_QUERY_KEY = ["dashboard", "summary"] as const;

export interface UseDashboardSummaryReturn {
  summary: DashboardSummaryResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
  refetch: () => void;
}

/** One request for the whole dashboard — see `dashboard_service.py`'s
 * docstring for why this stays a single composed endpoint instead of one
 * request per widget. */
export function useDashboardSummary(): UseDashboardSummaryReturn {
  const result = useQuery({
    queryKey: DASHBOARD_SUMMARY_QUERY_KEY,
    queryFn: ({ signal }) => dashboardService.getDashboardSummary(signal),
  });

  return {
    summary: result.data,
    isLoading: result.isLoading,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
    refetch: () => void result.refetch(),
  };
}
