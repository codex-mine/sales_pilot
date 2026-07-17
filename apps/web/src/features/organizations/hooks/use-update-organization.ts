"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { useAuthStore } from "@/store/auth-store";
import { organizationService } from "../services/organization.service";
import type { OrganizationDetailResponse, OrganizationUpdateRequest } from "../types";
import { ORGANIZATION_DETAIL_QUERY_KEY } from "./use-organization-detail";

export interface UseUpdateOrganizationReturn {
  /** Promise-based so the calling form can `await`/`try-catch` and map field errors itself (same pattern as the auth forms). */
  updateOrganization: (payload: OrganizationUpdateRequest) => Promise<OrganizationDetailResponse>;
  isUpdating: boolean;
}

/** Updates the current organization (profile fields or settings fields — same endpoint, PATCH is partial). Keeps the auth store's cached `organization`/`workspace` (sidebar, header) in sync on success. */
export function useUpdateOrganization(): UseUpdateOrganizationReturn {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: async (payload: OrganizationUpdateRequest) => {
      const cached = queryClient.getQueryData<OrganizationDetailResponse>(
        ORGANIZATION_DETAIL_QUERY_KEY,
      );
      const organizationId = cached?.id ?? (await organizationService.getCurrentOrganization()).id;
      return organizationService.updateOrganization(organizationId, payload);
    },
    onSuccess: (organization) => {
      queryClient.setQueryData(ORGANIZATION_DETAIL_QUERY_KEY, organization);
      toast.success("Organization updated.");
      void useAuthStore.getState().loadUser();
    },
  });

  return {
    updateOrganization: (payload) => mutation.mutateAsync(payload),
    isUpdating: mutation.isPending,
  };
}
