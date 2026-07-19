"use client";

import { useQuery } from "@tanstack/react-query";
import { normalizeApiError } from "@/lib/api/errors";
import { campaignService } from "../services/campaign.service";
import type { CampaignResponse, CampaignsQuery, PaginationMeta } from "../types";

export const CAMPAIGNS_QUERY_KEY = (query: CampaignsQuery) => ["campaigns", "list", query] as const;

export interface UseCampaignsReturn {
  campaigns: CampaignResponse[];
  meta: PaginationMeta;
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
  refetch: () => void;
}

export function useCampaigns(query: CampaignsQuery = {}): UseCampaignsReturn {
  const result = useQuery({
    queryKey: CAMPAIGNS_QUERY_KEY(query),
    queryFn: ({ signal }) => campaignService.getCampaigns(query, signal),
    placeholderData: (previous) => previous,
  });

  return {
    campaigns: result.data?.campaigns ?? [],
    meta: result.data?.meta ?? { page: 1, page_size: 25, total: 0 },
    isLoading: result.isLoading,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
    refetch: () => void result.refetch(),
  };
}
