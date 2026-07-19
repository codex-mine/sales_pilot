"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { normalizeApiError } from "@/lib/api/errors";
import { campaignService } from "../services/campaign.service";
import type { CampaignResponse, CreateCampaignRequest, UpdateCampaignRequest } from "../types";
import { CAMPAIGN_QUERY_KEY } from "./use-campaign";

export interface UseCreateCampaignReturn {
  createCampaign: (payload: CreateCampaignRequest) => Promise<CampaignResponse>;
  isCreating: boolean;
}

export function useCreateCampaign(): UseCreateCampaignReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (payload: CreateCampaignRequest) => campaignService.createCampaign(payload),
    onSuccess: () => {
      toast.success("Campaign created.");
      void queryClient.invalidateQueries({ queryKey: ["campaigns", "list"] });
    },
  });
  return { createCampaign: (payload) => mutation.mutateAsync(payload), isCreating: mutation.isPending };
}

export interface UseUpdateCampaignReturn {
  updateCampaign: (args: { campaignId: string; payload: UpdateCampaignRequest }) => Promise<CampaignResponse>;
  isUpdating: boolean;
}

export function useUpdateCampaign(): UseUpdateCampaignReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ campaignId, payload }: { campaignId: string; payload: UpdateCampaignRequest }) =>
      campaignService.updateCampaign(campaignId, payload),
    onSuccess: (campaign) => {
      queryClient.setQueryData(CAMPAIGN_QUERY_KEY(campaign.id), campaign);
      void queryClient.invalidateQueries({ queryKey: ["campaigns", "list"] });
      toast.success("Campaign updated.");
    },
  });
  return { updateCampaign: (args) => mutation.mutateAsync(args), isUpdating: mutation.isPending };
}

export interface UseDeleteCampaignReturn {
  deleteCampaign: (campaignId: string) => Promise<void>;
  isDeleting: boolean;
}

export function useDeleteCampaign(): UseDeleteCampaignReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (campaignId: string) => campaignService.deleteCampaign(campaignId),
    onSuccess: () => {
      toast.success("Campaign deleted.");
      void queryClient.invalidateQueries({ queryKey: ["campaigns", "list"] });
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });
  return { deleteCampaign: (campaignId) => mutation.mutateAsync(campaignId), isDeleting: mutation.isPending };
}

export interface UseCampaignStatusControlReturn {
  activateCampaign: (campaignId: string) => Promise<CampaignResponse>;
  isActivating: boolean;
  pauseCampaign: (campaignId: string) => Promise<CampaignResponse>;
  isPausing: boolean;
  archiveCampaign: (campaignId: string) => Promise<CampaignResponse>;
  isArchiving: boolean;
}

/** Draft -> active -> paused -> completed -> archived — every transition here
 * goes through a dedicated status-control endpoint (never PATCH), mirroring
 * the backend's explicit `activate`/`pause`/`archive` service methods. */
export function useCampaignStatusControl(): UseCampaignStatusControlReturn {
  const queryClient = useQueryClient();

  function onSettled(campaign: CampaignResponse, message: string): void {
    queryClient.setQueryData(CAMPAIGN_QUERY_KEY(campaign.id), campaign);
    void queryClient.invalidateQueries({ queryKey: ["campaigns", "list"] });
    toast.success(message);
  }

  const activateMutation = useMutation({
    mutationFn: (campaignId: string) => campaignService.activateCampaign(campaignId),
    onSuccess: (campaign) => onSettled(campaign, "Campaign activated."),
    onError: (error) => toast.error(normalizeApiError(error).message),
  });

  const pauseMutation = useMutation({
    mutationFn: (campaignId: string) => campaignService.pauseCampaign(campaignId),
    onSuccess: (campaign) => onSettled(campaign, "Campaign paused."),
    onError: (error) => toast.error(normalizeApiError(error).message),
  });

  const archiveMutation = useMutation({
    mutationFn: (campaignId: string) => campaignService.archiveCampaign(campaignId),
    onSuccess: (campaign) => onSettled(campaign, "Campaign archived."),
    onError: (error) => toast.error(normalizeApiError(error).message),
  });

  return {
    activateCampaign: (campaignId) => activateMutation.mutateAsync(campaignId),
    isActivating: activateMutation.isPending,
    pauseCampaign: (campaignId) => pauseMutation.mutateAsync(campaignId),
    isPausing: pauseMutation.isPending,
    archiveCampaign: (campaignId) => archiveMutation.mutateAsync(campaignId),
    isArchiving: archiveMutation.isPending,
  };
}
