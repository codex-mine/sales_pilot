"use client";

import { useQuery } from "@tanstack/react-query";
import { normalizeApiError } from "@/lib/api/errors";
import { leadService } from "../services/lead.service";
import type { ActivityResponse, PaginationMeta } from "../types";

export interface UseLeadActivitiesReturn {
  activities: ActivityResponse[];
  meta: PaginationMeta;
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
}

export function useLeadActivities(leadId: string, page = 1, pageSize = 50): UseLeadActivitiesReturn {
  const query = useQuery({
    queryKey: ["leads", "activities", leadId, page, pageSize] as const,
    queryFn: () => leadService.getActivities(leadId, page, pageSize),
    enabled: Boolean(leadId),
  });

  return {
    activities: query.data?.activities ?? [],
    meta: query.data?.meta ?? { page, page_size: pageSize, total: 0 },
    isLoading: query.isLoading,
    isError: query.isError,
    errorMessage: query.error ? normalizeApiError(query.error).message : null,
  };
}
