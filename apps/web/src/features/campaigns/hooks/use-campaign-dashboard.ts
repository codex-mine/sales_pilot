"use client";

import { useQuery } from "@tanstack/react-query";
import { normalizeApiError } from "@/lib/api/errors";
import { campaignService } from "../services/campaign.service";
import type { CampaignDashboardResponse } from "../types";

export const CAMPAIGN_DASHBOARD_QUERY_KEY = (campaignId: string) => ["campaigns", "dashboard", campaignId] as const;

export interface UseCampaignDashboardReturn {
  dashboard: CampaignDashboardResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
  refetch: () => void;
}

export function useCampaignDashboard(campaignId: string): UseCampaignDashboardReturn {
  const result = useQuery({
    queryKey: CAMPAIGN_DASHBOARD_QUERY_KEY(campaignId),
    queryFn: ({ signal }) => campaignService.getCampaignDashboard(campaignId, signal),
    enabled: Boolean(campaignId),
  });

  return {
    dashboard: result.data,
    isLoading: result.isLoading,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
    refetch: () => void result.refetch(),
  };
}
