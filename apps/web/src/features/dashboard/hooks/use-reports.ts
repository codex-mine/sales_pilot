"use client";

import { useQuery } from "@tanstack/react-query";
import { normalizeApiError } from "@/lib/api/errors";
import { dashboardService } from "../services/dashboard.service";
import type { PaginationMeta, ReportResponse } from "../types";

export const REPORTS_QUERY_KEY = (page: number, pageSize: number) => ["reports", "list", page, pageSize] as const;

export interface UseReportsReturn {
  reports: ReportResponse[];
  meta: PaginationMeta;
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
  refetch: () => void;
}

export function useReports(page = 1, pageSize = 25): UseReportsReturn {
  const result = useQuery({
    queryKey: REPORTS_QUERY_KEY(page, pageSize),
    queryFn: ({ signal }) => dashboardService.getReports({ page, page_size: pageSize }, signal),
    placeholderData: (previous) => previous,
  });

  return {
    reports: result.data?.reports ?? [],
    meta: result.data?.meta ?? { page: 1, page_size: pageSize, total: 0 },
    isLoading: result.isLoading,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
    refetch: () => void result.refetch(),
  };
}
