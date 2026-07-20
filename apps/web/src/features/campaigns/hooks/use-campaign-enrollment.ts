"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { normalizeApiError } from "@/lib/api/errors";
import { campaignService } from "../services/campaign.service";
import type {
  BulkEnrollRequest,
  BulkEnrollResponse,
  CampaignLeadResponse,
  EnrollByFilterRequest,
  EnrollLeadRequest,
} from "../types";
import { CAMPAIGN_QUERY_KEY } from "./use-campaign";

function invalidateCampaignLeads(queryClient: ReturnType<typeof useQueryClient>, campaignId: string): void {
  void queryClient.invalidateQueries({ queryKey: ["campaigns", "leads", campaignId] });
  void queryClient.invalidateQueries({ queryKey: CAMPAIGN_QUERY_KEY(campaignId) });
  void queryClient.invalidateQueries({ queryKey: ["campaigns", "list"] });
}

export interface UseEnrollLeadReturn {
  enrollLead: (args: { campaignId: string; payload: EnrollLeadRequest }) => Promise<CampaignLeadResponse>;
  isEnrolling: boolean;
}

export function useEnrollLead(): UseEnrollLeadReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ campaignId, payload }: { campaignId: string; payload: EnrollLeadRequest }) =>
      campaignService.enrollLead(campaignId, payload),
    onSuccess: (_campaignLead, variables) => {
      invalidateCampaignLeads(queryClient, variables.campaignId);
      void queryClient.invalidateQueries({ queryKey: ["leads", "campaigns"] });
      toast.success("Lead enrolled.");
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });
  return { enrollLead: (args) => mutation.mutateAsync(args), isEnrolling: mutation.isPending };
}

export interface UseBulkEnrollLeadsReturn {
  bulkEnroll: (args: { campaignId: string; payload: BulkEnrollRequest }) => Promise<BulkEnrollResponse>;
  isEnrolling: boolean;
}

export function useBulkEnrollLeads(): UseBulkEnrollLeadsReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ campaignId, payload }: { campaignId: string; payload: BulkEnrollRequest }) =>
      campaignService.enrollBulk(campaignId, payload),
    onSuccess: (result, variables) => {
      invalidateCampaignLeads(queryClient, variables.campaignId);
      void queryClient.invalidateQueries({ queryKey: ["leads", "campaigns"] });
      toast.success(`${result.enrolled_count} of ${result.requested_count} lead(s) enrolled.`);
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });
  return { bulkEnroll: (args) => mutation.mutateAsync(args), isEnrolling: mutation.isPending };
}

export interface UseEnrollByFilterReturn {
  enrollByFilter: (args: { campaignId: string; payload: EnrollByFilterRequest }) => Promise<BulkEnrollResponse>;
  isEnrolling: boolean;
}

export function useEnrollByFilter(): UseEnrollByFilterReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ campaignId, payload }: { campaignId: string; payload: EnrollByFilterRequest }) =>
      campaignService.enrollByFilter(campaignId, payload),
    onSuccess: (result, variables) => {
      invalidateCampaignLeads(queryClient, variables.campaignId);
      toast.success(`${result.enrolled_count} of ${result.requested_count} lead(s) enrolled.`);
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });
  return { enrollByFilter: (args) => mutation.mutateAsync(args), isEnrolling: mutation.isPending };
}

export interface UseUnenrollCampaignLeadReturn {
  unenroll: (args: { campaignId: string; campaignLeadId: string; reason?: string }) => Promise<CampaignLeadResponse>;
  isUnenrolling: boolean;
}

export function useUnenrollCampaignLead(): UseUnenrollCampaignLeadReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ campaignLeadId, reason }: { campaignId: string; campaignLeadId: string; reason?: string }) =>
      campaignService.unenrollCampaignLead(campaignLeadId, reason),
    onSuccess: (_campaignLead, variables) => {
      invalidateCampaignLeads(queryClient, variables.campaignId);
      void queryClient.invalidateQueries({ queryKey: ["leads", "campaigns"] });
      toast.success("Lead unenrolled.");
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });
  return { unenroll: (args) => mutation.mutateAsync(args), isUnenrolling: mutation.isPending };
}
