"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { normalizeApiError } from "@/lib/api/errors";
import { leadService } from "../services/lead.service";
import type { LeadCreateRequest, LeadResponse, LeadUpdateRequest } from "../types";
import { LEAD_QUERY_KEY } from "./use-lead";

export interface UseCreateLeadReturn {
  createLead: (payload: LeadCreateRequest) => Promise<LeadResponse>;
  isCreating: boolean;
}

export function useCreateLead(): UseCreateLeadReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (payload: LeadCreateRequest) => leadService.createLead(payload),
    onSuccess: () => {
      toast.success("Lead created.");
      void queryClient.invalidateQueries({ queryKey: ["leads", "list"] });
    },
  });
  return { createLead: (payload) => mutation.mutateAsync(payload), isCreating: mutation.isPending };
}

export interface UseUpdateLeadReturn {
  updateLead: (args: { leadId: string; payload: LeadUpdateRequest }) => Promise<LeadResponse>;
  isUpdating: boolean;
}

export function useUpdateLead(): UseUpdateLeadReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ leadId, payload }: { leadId: string; payload: LeadUpdateRequest }) =>
      leadService.updateLead(leadId, payload),
    onSuccess: (lead) => {
      queryClient.setQueryData(LEAD_QUERY_KEY(lead.id), lead);
      void queryClient.invalidateQueries({ queryKey: ["leads", "list"] });
      void queryClient.invalidateQueries({ queryKey: ["leads", "activities", lead.id] });
    },
  });
  return {
    updateLead: (args) => mutation.mutateAsync(args),
    isUpdating: mutation.isPending,
  };
}

/** Toggles favorite/archived without a success toast — used for the quick-action star/archive buttons where a toast per click would be noisy. */
export function useToggleLeadFlag(): {
  toggleFavorite: (lead: LeadResponse) => void;
  toggleArchived: (lead: LeadResponse) => void;
} {
  const { updateLead } = useUpdateLead();
  return {
    toggleFavorite: (lead) => {
      void updateLead({ leadId: lead.id, payload: { is_favorite: !lead.is_favorite } }).catch((error) =>
        toast.error(normalizeApiError(error).message),
      );
    },
    toggleArchived: (lead) => {
      void updateLead({ leadId: lead.id, payload: { is_archived: !lead.is_archived } })
        .then(() => toast.success(lead.is_archived ? "Lead restored." : "Lead archived."))
        .catch((error) => toast.error(normalizeApiError(error).message));
    },
  };
}

export interface UseDeleteLeadReturn {
  deleteLead: (leadId: string) => Promise<void>;
  isDeleting: boolean;
}

export function useDeleteLead(): UseDeleteLeadReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (leadId: string) => leadService.deleteLead(leadId),
    onSuccess: () => {
      toast.success("Lead deleted.");
      void queryClient.invalidateQueries({ queryKey: ["leads", "list"] });
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });
  return { deleteLead: (leadId) => mutation.mutateAsync(leadId), isDeleting: mutation.isPending };
}
