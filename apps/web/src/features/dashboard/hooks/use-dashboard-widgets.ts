"use client";

import { useQuery } from "@tanstack/react-query";
import { normalizeApiError } from "@/lib/api/errors";
import { dashboardService } from "../services/dashboard.service";
import type { DashboardWidgetResponse } from "../types";

export const DASHBOARD_WIDGETS_QUERY_KEY = ["dashboard", "widgets"] as const;

export interface UseDashboardWidgetsReturn {
  widgets: DashboardWidgetResponse[];
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
  refetch: () => void;
}

export function useDashboardWidgets(): UseDashboardWidgetsReturn {
  const result = useQuery({
    queryKey: DASHBOARD_WIDGETS_QUERY_KEY,
    queryFn: ({ signal }) => dashboardService.getDashboardWidgets(signal),
  });

  return {
    widgets: result.data ?? [],
    isLoading: result.isLoading,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
    refetch: () => void result.refetch(),
  };
}
