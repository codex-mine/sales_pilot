"use client";

import { useQuery } from "@tanstack/react-query";
import { normalizeApiError } from "@/lib/api/errors";
import { leadService } from "../services/lead.service";
import type { LeadResponse, LeadsQuery, PaginationMeta } from "../types";

export const LEADS_QUERY_KEY = (query: LeadsQuery) => ["leads", "list", query] as const;

export interface UseLeadsReturn {
  leads: LeadResponse[];
  meta: PaginationMeta;
  isLoading: boolean;
  isFetching: boolean;
  isError: boolean;
  errorMessage: string | null;
  refetch: () => void;
}

/** Server-side search/filter/sort/pagination — pass the full query object as component state (see leads-table.tsx). */
export function useLeads(query: LeadsQuery): UseLeadsReturn {
  const result = useQuery({
    queryKey: LEADS_QUERY_KEY(query),
    queryFn: ({ signal }) => leadService.getLeads(query, signal),
    placeholderData: (previous) => previous,
  });

  return {
    leads: result.data?.leads ?? [],
    meta: result.data?.meta ?? { page: query.page ?? 1, page_size: query.page_size ?? 25, total: 0 },
    isLoading: result.isLoading,
    isFetching: result.isFetching,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
    refetch: () => void result.refetch(),
  };
}
