"use client";

import { useAuthStore } from "@/store/auth-store";
import type { OrganizationResponse } from "@/features/auth/types";

export interface UseOrganizationReturn {
  organization: OrganizationResponse | null;
  /** Alias for `organization` today — see the auth store's docstring on why "workspace" and "organization" are the same tenant boundary in this schema. */
  workspace: OrganizationResponse | null;
  selectedOrganizationId: string | null;
  setSelectedOrganization: (organizationId: string) => void;
}

export function useOrganization(): UseOrganizationReturn {
  const organization = useAuthStore((state) => state.organization);
  const workspace = useAuthStore((state) => state.workspace);
  const selectedOrganizationId = useAuthStore((state) => state.selectedOrganizationId);
  const setSelectedOrganization = useAuthStore((state) => state.setSelectedOrganization);

  return { organization, workspace, selectedOrganizationId, setSelectedOrganization };
}
