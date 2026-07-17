"use client";

import { useQuery } from "@tanstack/react-query";
import { normalizeApiError } from "@/lib/api/errors";
import { companyService } from "../services/company.service";
import type { CompaniesQuery, CompanyResponse, PaginationMeta } from "../types";

export const COMPANIES_QUERY_KEY = (query: CompaniesQuery) => ["companies", "list", query] as const;

export interface UseCompaniesReturn {
  companies: CompanyResponse[];
  meta: PaginationMeta;
  isLoading: boolean;
  isFetching: boolean;
  isError: boolean;
  errorMessage: string | null;
  refetch: () => void;
}

/** Server-side search/filter/sort/pagination — pass the full query object as component state (see companies-table.tsx). */
export function useCompanies(query: CompaniesQuery): UseCompaniesReturn {
  const result = useQuery({
    queryKey: COMPANIES_QUERY_KEY(query),
    queryFn: ({ signal }) => companyService.getCompanies(query, signal),
    placeholderData: (previous) => previous,
  });

  return {
    companies: result.data?.companies ?? [],
    meta: result.data?.meta ?? { page: query.page ?? 1, page_size: query.page_size ?? 25, total: 0 },
    isLoading: result.isLoading,
    isFetching: result.isFetching,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
    refetch: () => void result.refetch(),
  };
}
