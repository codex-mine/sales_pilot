"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { normalizeApiError } from "@/lib/api/errors";
import { campaignService } from "../services/campaign.service";
import type {
  CreateSequenceRequest,
  CreateSequenceStepRequest,
  SequenceResponse,
  SequenceStepResponse,
  UpdateSequenceRequest,
  UpdateSequenceStepRequest,
} from "../types";
import { CAMPAIGN_SEQUENCES_QUERY_KEY } from "./use-campaign-sequence";

export interface UseCreateSequenceReturn {
  createSequence: (args: { campaignId: string; payload: CreateSequenceRequest }) => Promise<SequenceResponse>;
  isCreating: boolean;
}

export function useCreateSequence(): UseCreateSequenceReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ campaignId, payload }: { campaignId: string; payload: CreateSequenceRequest }) =>
      campaignService.createCampaignSequence(campaignId, payload),
    onSuccess: (_sequence, variables) => {
      void queryClient.invalidateQueries({ queryKey: CAMPAIGN_SEQUENCES_QUERY_KEY(variables.campaignId) });
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });
  return { createSequence: (args) => mutation.mutateAsync(args), isCreating: mutation.isPending };
}

export interface UseUpdateSequenceReturn {
  updateSequence: (args: {
    campaignId: string;
    sequenceId: string;
    payload: UpdateSequenceRequest;
  }) => Promise<SequenceResponse>;
  isUpdating: boolean;
}

export function useUpdateSequence(): UseUpdateSequenceReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ sequenceId, payload }: { campaignId: string; sequenceId: string; payload: UpdateSequenceRequest }) =>
      campaignService.updateSequence(sequenceId, payload),
    onSuccess: (_sequence, variables) => {
      void queryClient.invalidateQueries({ queryKey: CAMPAIGN_SEQUENCES_QUERY_KEY(variables.campaignId) });
      toast.success("Sequence updated.");
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });
  return { updateSequence: (args) => mutation.mutateAsync(args), isUpdating: mutation.isPending };
}

export interface UseCreateSequenceStepReturn {
  createStep: (args: {
    campaignId: string;
    sequenceId: string;
    payload: CreateSequenceStepRequest;
  }) => Promise<SequenceStepResponse>;
  isCreating: boolean;
}

export function useCreateSequenceStep(): UseCreateSequenceStepReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ sequenceId, payload }: { campaignId: string; sequenceId: string; payload: CreateSequenceStepRequest }) =>
      campaignService.createSequenceStep(sequenceId, payload),
    onSuccess: (_step, variables) => {
      void queryClient.invalidateQueries({ queryKey: CAMPAIGN_SEQUENCES_QUERY_KEY(variables.campaignId) });
      toast.success("Step added.");
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });
  return { createStep: (args) => mutation.mutateAsync(args), isCreating: mutation.isPending };
}

export interface UseUpdateSequenceStepReturn {
  updateStep: (args: {
    campaignId: string;
    stepId: string;
    payload: UpdateSequenceStepRequest;
  }) => Promise<SequenceStepResponse>;
  isUpdating: boolean;
}

export function useUpdateSequenceStep(): UseUpdateSequenceStepReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ stepId, payload }: { campaignId: string; stepId: string; payload: UpdateSequenceStepRequest }) =>
      campaignService.updateSequenceStep(stepId, payload),
    onSuccess: (_step, variables) => {
      void queryClient.invalidateQueries({ queryKey: CAMPAIGN_SEQUENCES_QUERY_KEY(variables.campaignId) });
      toast.success("Step updated.");
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });
  return { updateStep: (args) => mutation.mutateAsync(args), isUpdating: mutation.isPending };
}

export interface UseDeleteSequenceStepReturn {
  deleteStep: (args: { campaignId: string; stepId: string }) => Promise<void>;
  isDeleting: boolean;
}

export function useDeleteSequenceStep(): UseDeleteSequenceStepReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ stepId }: { campaignId: string; stepId: string }) => campaignService.deleteSequenceStep(stepId),
    onSuccess: (_void, variables) => {
      void queryClient.invalidateQueries({ queryKey: CAMPAIGN_SEQUENCES_QUERY_KEY(variables.campaignId) });
      toast.success("Step deleted.");
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });
  return { deleteStep: (args) => mutation.mutateAsync(args), isDeleting: mutation.isPending };
}

export interface UseMoveSequenceStepReturn {
  moveStep: (args: { campaignId: string; stepId: string; direction: "up" | "down" }) => Promise<SequenceStepResponse[]>;
  isMoving: boolean;
}

export function useMoveSequenceStep(): UseMoveSequenceStepReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ stepId, direction }: { campaignId: string; stepId: string; direction: "up" | "down" }) =>
      campaignService.moveSequenceStep(stepId, direction),
    onSuccess: (_steps, variables) => {
      void queryClient.invalidateQueries({ queryKey: CAMPAIGN_SEQUENCES_QUERY_KEY(variables.campaignId) });
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });
  return { moveStep: (args) => mutation.mutateAsync(args), isMoving: mutation.isPending };
}
