"use client";

import { useQuery } from "@tanstack/react-query";
import { normalizeApiError } from "@/lib/api/errors";
import { campaignService } from "../services/campaign.service";
import type { CampaignResponse } from "../types";

export const CAMPAIGN_QUERY_KEY = (campaignId: string) => ["campaigns", "detail", campaignId] as const;

export interface UseCampaignReturn {
  campaign: CampaignResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
  refetch: () => void;
}

export function useCampaign(campaignId: string): UseCampaignReturn {
  const result = useQuery({
    queryKey: CAMPAIGN_QUERY_KEY(campaignId),
    queryFn: ({ signal }) => campaignService.getCampaign(campaignId, signal),
    enabled: Boolean(campaignId),
  });

  return {
    campaign: result.data,
    isLoading: result.isLoading,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
    refetch: () => void result.refetch(),
  };
}
