"use client";

import { useQuery } from "@tanstack/react-query";
import { normalizeApiError } from "@/lib/api/errors";
import { companyService } from "../services/company.service";
import type { CompanyResponse } from "../types";

export const COMPANY_QUERY_KEY = (companyId: string) => ["companies", "detail", companyId] as const;

export interface UseCompanyReturn {
  company: CompanyResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
  refetch: () => void;
}

export function useCompany(companyId: string): UseCompanyReturn {
  const result = useQuery({
    queryKey: COMPANY_QUERY_KEY(companyId),
    queryFn: ({ signal }) => companyService.getCompany(companyId, signal),
    enabled: Boolean(companyId),
  });

  return {
    company: result.data,
    isLoading: result.isLoading,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
    refetch: () => void result.refetch(),
  };
}
