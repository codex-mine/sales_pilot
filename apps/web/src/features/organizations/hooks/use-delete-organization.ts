"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { organizationService } from "../services/organization.service";
import type { OrganizationDetailResponse } from "../types";
import { ORGANIZATION_DETAIL_QUERY_KEY } from "./use-organization-detail";

export interface UseDeleteOrganizationReturn {
  /** Promise-based — deleting your own organization also ends your session (see backend), so the caller is responsible for clearing auth state and redirecting on success. */
  deleteOrganization: () => Promise<void>;
  isDeleting: boolean;
}

export function useDeleteOrganization(): UseDeleteOrganizationReturn {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: async () => {
      const cached = queryClient.getQueryData<OrganizationDetailResponse>(
        ORGANIZATION_DETAIL_QUERY_KEY,
      );
      const organizationId = cached?.id ?? (await organizationService.getCurrentOrganization()).id;
      await organizationService.deleteOrganization(organizationId);
    },
  });

  return {
    deleteOrganization: () => mutation.mutateAsync(),
    isDeleting: mutation.isPending,
  };
}
