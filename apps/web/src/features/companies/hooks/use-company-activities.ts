"use client";

import { useQuery } from "@tanstack/react-query";
import { normalizeApiError } from "@/lib/api/errors";
import { companyService } from "../services/company.service";
import type { CompanyActivityResponse, PaginationMeta } from "../types";

export interface UseCompanyActivitiesReturn {
  activities: CompanyActivityResponse[];
  meta: PaginationMeta;
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
}

export function useCompanyActivities(companyId: string, page = 1, pageSize = 50): UseCompanyActivitiesReturn {
  const query = useQuery({
    queryKey: ["companies", "activities", companyId, page, pageSize] as const,
    queryFn: () => companyService.getCompanyActivities(companyId, page, pageSize),
    enabled: Boolean(companyId),
  });

  return {
    activities: query.data?.activities ?? [],
    meta: query.data?.meta ?? { page, page_size: pageSize, total: 0 },
    isLoading: query.isLoading,
    isError: query.isError,
    errorMessage: query.error ? normalizeApiError(query.error).message : null,
  };
}
