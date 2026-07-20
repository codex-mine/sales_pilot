"use client";

import { useQuery } from "@tanstack/react-query";
import { normalizeApiError } from "@/lib/api/errors";
import { campaignService } from "../services/campaign.service";
import type { SequenceResponse } from "../types";

export const CAMPAIGN_SEQUENCES_QUERY_KEY = (campaignId: string) => ["campaigns", "sequences", campaignId] as const;

export interface UseCampaignSequenceReturn {
  /** V1 scope is a single sequence per campaign — the first (and normally only) one. */
  sequence: SequenceResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
  refetch: () => void;
}

export function useCampaignSequence(campaignId: string): UseCampaignSequenceReturn {
  const result = useQuery({
    queryKey: CAMPAIGN_SEQUENCES_QUERY_KEY(campaignId),
    queryFn: ({ signal }) => campaignService.getCampaignSequences(campaignId, signal),
    enabled: Boolean(campaignId),
  });

  return {
    sequence: result.data?.[0],
    isLoading: result.isLoading,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
    refetch: () => void result.refetch(),
  };
}
