"use client";

import { useQuery } from "@tanstack/react-query";
import { normalizeApiError } from "@/lib/api/errors";
import { campaignService } from "../services/campaign.service";
import type { CampaignLeadResponse } from "../types";

export const LEAD_CAMPAIGNS_QUERY_KEY = (leadId: string) => ["leads", "campaigns", leadId] as const;

export interface UseLeadCampaignsReturn {
  campaignLeads: CampaignLeadResponse[];
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
  refetch: () => void;
}

export function useLeadCampaigns(leadId: string): UseLeadCampaignsReturn {
  const result = useQuery({
    queryKey: LEAD_CAMPAIGNS_QUERY_KEY(leadId),
    queryFn: ({ signal }) => campaignService.getLeadCampaigns(leadId, signal),
    enabled: Boolean(leadId),
  });

  return {
    campaignLeads: result.data ?? [],
    isLoading: result.isLoading,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
    refetch: () => void result.refetch(),
  };
}
