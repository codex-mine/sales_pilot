"use client";

import { useQuery } from "@tanstack/react-query";
import { normalizeApiError } from "@/lib/api/errors";
import { campaignService } from "../services/campaign.service";
import type { CampaignLeadResponse, CampaignLeadsQuery, PaginationMeta } from "../types";

export const CAMPAIGN_LEADS_QUERY_KEY = (campaignId: string, query: CampaignLeadsQuery) =>
  ["campaigns", "leads", campaignId, query] as const;

export interface UseCampaignLeadsReturn {
  campaignLeads: CampaignLeadResponse[];
  meta: PaginationMeta;
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
  refetch: () => void;
}

export function useCampaignLeads(campaignId: string, query: CampaignLeadsQuery = {}): UseCampaignLeadsReturn {
  const result = useQuery({
    queryKey: CAMPAIGN_LEADS_QUERY_KEY(campaignId, query),
    queryFn: ({ signal }) => campaignService.getCampaignLeads(campaignId, query, signal),
    enabled: Boolean(campaignId),
    placeholderData: (previous) => previous,
  });

  return {
    campaignLeads: result.data?.campaignLeads ?? [],
    meta: result.data?.meta ?? { page: 1, page_size: 25, total: 0 },
    isLoading: result.isLoading,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
    refetch: () => void result.refetch(),
  };
}
