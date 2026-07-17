"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { normalizeApiError } from "@/lib/api/errors";
import { useAuthStore } from "@/store/auth-store";
import { organizationService } from "../services/organization.service";
import type { OrganizationDetailResponse } from "../types";
import { ORGANIZATION_DETAIL_QUERY_KEY } from "./use-organization-detail";

function useOrganizationId(): () => Promise<string> {
  const queryClient = useQueryClient();
  return async () => {
    const cached = queryClient.getQueryData<OrganizationDetailResponse>(
      ORGANIZATION_DETAIL_QUERY_KEY,
    );
    return cached?.id ?? (await organizationService.getCurrentOrganization()).id;
  };
}

export interface UseOrganizationLogoReturn {
  uploadLogo: (file: File) => void;
  isUploading: boolean;
  removeLogo: () => void;
  isRemoving: boolean;
}

/** Upload/replace/remove the organization logo. Both mutations update the detail cache and the auth store (sidebar shows the logo too) on success. */
export function useOrganizationLogo(): UseOrganizationLogoReturn {
  const queryClient = useQueryClient();
  const getOrganizationId = useOrganizationId();

  function onLogoChanged(organization: OrganizationDetailResponse): void {
    queryClient.setQueryData(ORGANIZATION_DETAIL_QUERY_KEY, organization);
    void useAuthStore.getState().loadUser();
  }

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const organizationId = await getOrganizationId();
      return organizationService.uploadOrganizationLogo(organizationId, file);
    },
    onSuccess: (organization) => {
      onLogoChanged(organization);
      toast.success("Logo updated.");
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });

  const removeMutation = useMutation({
    mutationFn: async () => {
      const organizationId = await getOrganizationId();
      return organizationService.deleteOrganizationLogo(organizationId);
    },
    onSuccess: (organization) => {
      onLogoChanged(organization);
      toast.success("Logo removed.");
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });

  return {
    uploadLogo: (file) => uploadMutation.mutate(file),
    isUploading: uploadMutation.isPending,
    removeLogo: () => removeMutation.mutate(),
    isRemoving: removeMutation.isPending,
  };
}
