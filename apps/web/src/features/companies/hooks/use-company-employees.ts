"use client";

import { useQuery } from "@tanstack/react-query";
import { normalizeApiError } from "@/lib/api/errors";
import { companyService } from "../services/company.service";
import type { CompanyEmployeeResponse, PaginationMeta } from "../types";

export interface UseCompanyEmployeesReturn {
  employees: CompanyEmployeeResponse[];
  meta: PaginationMeta;
  isLoading: boolean;
  isFetching: boolean;
  isError: boolean;
  errorMessage: string | null;
}

export interface CompanyEmployeesQuery {
  search?: string;
  status?: string;
  page?: number;
  page_size?: number;
}

/** Read-only Contact list scoped to a company. Full employee management is a future Contacts module (per spec). */
export function useCompanyEmployees(companyId: string, query: CompanyEmployeesQuery): UseCompanyEmployeesReturn {
  const result = useQuery({
    queryKey: ["companies", "employees", companyId, query] as const,
    queryFn: ({ signal }) => companyService.getCompanyEmployees(companyId, query, signal),
    enabled: Boolean(companyId),
    placeholderData: (previous) => previous,
  });

  return {
    employees: result.data?.employees ?? [],
    meta: result.data?.meta ?? { page: query.page ?? 1, page_size: query.page_size ?? 25, total: 0 },
    isLoading: result.isLoading,
    isFetching: result.isFetching,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
  };
}
