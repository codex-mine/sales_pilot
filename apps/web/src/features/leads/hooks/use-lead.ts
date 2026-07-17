"use client";

import { useQuery } from "@tanstack/react-query";
import { normalizeApiError } from "@/lib/api/errors";
import { leadService } from "../services/lead.service";
import type { LeadResponse } from "../types";

export const LEAD_QUERY_KEY = (leadId: string) => ["leads", "detail", leadId] as const;

export interface UseLeadReturn {
  lead: LeadResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
  refetch: () => void;
}

export function useLead(leadId: string): UseLeadReturn {
  const result = useQuery({
    queryKey: LEAD_QUERY_KEY(leadId),
    queryFn: ({ signal }) => leadService.getLead(leadId, signal),
    enabled: Boolean(leadId),
  });

  return {
    lead: result.data,
    isLoading: result.isLoading,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
    refetch: () => void result.refetch(),
  };
}
